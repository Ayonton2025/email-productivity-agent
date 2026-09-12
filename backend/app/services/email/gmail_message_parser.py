"""Gmail message parser."""

import base64
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from .gmail_html import GmailHtmlProcessor

logger = logging.getLogger("app.services.gmail_ingestion_service")


def message_uid(internal_date, received_at):
    """Use epoch milliseconds for the numeric DB field; Gmail IDs stay opaque."""
    try:
        value = int(internal_date)
        if 0 <= value <= 2**63 - 1:
            return value
    except (TypeError, ValueError, OverflowError):
        pass
    if received_at.tzinfo is None:
        received_at = received_at.replace(tzinfo=timezone.utc)
    return int(received_at.timestamp() * 1000)


class GmailMessageParser:
    def parse_gmail_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a Gmail message into email fields.

        Properly extracts HTML content (preferred) and text fallback.
        Handles inline images (CID) and attachments.

        Args:
            message: Gmail message object from API

        Returns:
            Parsed email dictionary with html_body and body_text
        """
        try:
            headers = message["payload"].get("headers", [])
            headers_dict = {h["name"]: h["value"] for h in headers}

            # Extract basic fields
            sender = headers_dict.get("From", "Unknown")
            subject = headers_dict.get("Subject", "(No Subject)")
            message_id = headers_dict.get("Message-ID", "")

            # Parse recipients
            to = headers_dict.get("To", "").split(",")
            to = [t.strip() for t in to if t.strip()]

            cc = headers_dict.get("Cc", "").split(",")
            cc = [c.strip() for c in cc if c.strip()]

            # Parse timestamp
            received_at = headers_dict.get("Date", "")
            try:
                from email.utils import parsedate_to_datetime

                received_at = parsedate_to_datetime(received_at)
            except Exception:
                received_at = datetime.utcnow()
            if received_at.tzinfo is None:
                received_at = received_at.replace(tzinfo=timezone.utc)
            received_at = received_at.astimezone(timezone.utc).replace(tzinfo=None)

            # Extract email bodies (prefer HTML over text)
            body_text, body_html = self._extract_body(message["payload"])

            # Extract attachments
            attachments = self._extract_attachments(message["payload"])

            # Sanitize and process HTML
            if body_html:
                # Remove inline images first, we'll handle them separately
                body_html = self._sanitize_html(body_html)
                # Resolve CID (inline image) references
                body_html = self._resolve_cid_images(body_html, attachments)

            # If no HTML, sanitize text
            if body_text and not body_html:
                body_text = body_text.strip()

            return {
                "message_id": message["id"],
                "external_id": message["id"],
                "uid": message_uid(message.get("internalDate"), received_at),
                "thread_id": message.get("threadId"),
                "sender": sender,
                "recipients": to,
                "cc": cc,
                "subject": subject,
                "body_text": body_text,
                "body_html": body_html,  # ✅ This is the key: send HTML to frontend
                "received_at": received_at,
                "attachments": attachments,
                "raw_headers": headers_dict,
                "is_read": "UNREAD" not in message.get("labelIds", []),
                "is_flagged": "STARRED" in message.get("labelIds", []),
                "is_spam": "SPAM" in message.get("labelIds", []),
                "is_draft": "DRAFT" in message.get("labelIds", []),
            }

        except Exception as e:
            logger.error(f"❌ Error parsing message: {type(e).__name__}")
            raise

    def _extract_body(self, payload: Dict[str, Any]) -> tuple:
        """Extract text and HTML body from message payload"""
        body_text = ""
        body_html = ""

        if "parts" in payload:
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "")

                if mime_type == "text/plain":
                    data = part.get("body", {}).get("data", "")
                    if data:
                        body_text = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")

                elif mime_type == "text/html":
                    data = part.get("body", {}).get("data", "")
                    if data:
                        body_html = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")

                # Recursively check nested parts
                if "parts" in part:
                    nested_text, nested_html = self._extract_body(part)
                    if nested_text and not body_text:
                        body_text = nested_text
                    if nested_html and not body_html:
                        body_html = nested_html
        else:
            # Single-part message
            data = payload.get("body", {}).get("data", "")
            if data:
                decoded = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")
                mime_type = payload.get("mimeType", "text/plain")

                if mime_type == "text/html":
                    body_html = decoded
                else:
                    body_text = decoded

        # Fallback: use HTML as text if needed
        if not body_text and body_html:
            body_text = self._html_to_text(body_html)

        return body_text, body_html

    def _html_to_text(self, html: str) -> str:
        """Simple HTML to plain text conversion"""
        # Remove script tags
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        # Remove style tags
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML tags
        html = re.sub(r"<[^>]+>", "\n", html)
        # Decode HTML entities
        html = html.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
        # Clean up whitespace
        lines = [line.strip() for line in html.split("\n") if line.strip()]
        return "\n".join(lines)

    def _extract_attachments(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract attachment metadata from message"""
        attachments = []

        def process_parts(parts: List[Dict[str, Any]]):
            for part in parts:
                if part.get("filename"):  # Has a filename = attachment
                    attachments.append(
                        {
                            "filename": part["filename"],
                            "mime_type": part.get("mimeType", ""),
                            "size": part.get("body", {}).get("size", 0),
                            "attachment_id": part.get("body", {}).get("attachmentId", ""),
                        }
                    )

                # Check nested parts
                if "parts" in part:
                    process_parts(part["parts"])

        if "parts" in payload:
            process_parts(payload["parts"])

        return attachments

    def _sanitize_html(self, html):
        return GmailHtmlProcessor()._sanitize_html(html)

    def _resolve_cid_images(self, html, attachments):
        return GmailHtmlProcessor()._resolve_cid_images(html, attachments)
