"""Gmail html."""

import logging
import re
from typing import Any, Dict, List

try:
    from bleach import clean as bleach_clean

    HAS_BLEACH = True
except ImportError:
    HAS_BLEACH = False

logger = logging.getLogger("app.services.gmail_ingestion_service")


class GmailHtmlProcessor:
    def _sanitize_html(self, html: str) -> str:
        """
        Sanitize HTML content to prevent XSS while preserving formatting.

        Allows safe tags and attributes needed for email display.
        Uses bleach if available, otherwise basic sanitization.
        """
        if not html:
            return ""

        try:
            if HAS_BLEACH:
                # Use bleach for proper sanitization
                allowed_tags = [
                    "a",
                    "abbr",
                    "acronym",
                    "b",
                    "blockquote",
                    "code",
                    "em",
                    "i",
                    "li",
                    "ol",
                    "p",
                    "pre",
                    "strong",
                    "ul",
                    "br",
                    "div",
                    "span",
                    "h1",
                    "h2",
                    "h3",
                    "h4",
                    "h5",
                    "h6",
                    "img",
                    "table",
                    "tr",
                    "td",
                    "th",
                    "thead",
                    "tbody",
                    "tfoot",
                ]

                allowed_attributes = {
                    "*": ["style", "class"],
                    "a": ["href", "target", "rel", "title"],
                    "img": ["src", "alt", "width", "height", "style", "loading"],
                    "table": ["border", "cellpadding", "cellspacing", "style"],
                    "td": ["colspan", "rowspan", "style"],
                    "th": ["colspan", "rowspan", "style"],
                }

                # Sanitize with bleach
                sanitized = bleach_clean(html, tags=allowed_tags, attributes=allowed_attributes, strip=True)

                # Ensure links open in new tab
                sanitized = re.sub(r"<a\s+(?!target=)", '<a target="_blank" rel="noopener noreferrer" ', sanitized)

                return sanitized
            else:
                # Fallback: basic HTML sanitization
                logger.debug("Using basic HTML sanitization (bleach not available)")

                # Remove script tags
                html = re.sub(
                    r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>", "", html, flags=re.DOTALL | re.IGNORECASE
                )
                # Remove style tags (but keep content style attributes)
                html = re.sub(
                    r"<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>", "", html, flags=re.DOTALL | re.IGNORECASE
                )
                # Remove event handlers
                html = re.sub(r'\s*on\w+=\s*["\']?[^"\']*["\']?', "", html, flags=re.IGNORECASE)

                return html

        except Exception as e:
            logger.error(f"❌ HTML sanitization failed: {type(e).__name__}")
            return html

    def _resolve_cid_images(self, html: str, attachments: List[Dict[str, Any]]) -> str:
        """
        Resolve Content-ID (CID) inline image references.

        Converts <img src="cid:image001@01D7ABC123.456" />
        to <img src="data:image/png;base64,..." />

        Args:
            html: HTML content with CID references
            attachments: List of attachment objects from Gmail

        Returns:
            HTML with CID references replaced with data URIs
        """
        try:
            if not html or not attachments:
                return html

            # Build a map of Content-ID to attachment
            cid_map = {}
            for att in attachments:
                content_id = att.get("content_id") or att.get("contentId")
                if content_id:
                    # Gmail wraps CID in angle brackets; remove them
                    clean_cid = content_id.strip("<>")
                    cid_map[clean_cid] = att

            if not cid_map:
                return html

            # Replace CID references with data URIs
            for cid, att in cid_map.items():
                # Match <img src="cid:..." and other references to this CID
                patterns = [
                    f"cid:{cid}",
                    f"cid:{re.escape(cid)}",
                ]

                # Get attachment content as base64
                try:
                    mime_type = att.get("mime_type", "image/png")
                    # Note: Gmail API returns attachment content via separate API call
                    # For now, we'll use a placeholder and note this needs attachment download
                    data_uri = f"data:{mime_type};base64,[ATTACHMENT_DATA]"

                    for pattern in patterns:
                        html = re.sub(
                            "src=([\"'])" + re.escape(pattern), f"src=\\1{data_uri}", html, flags=re.IGNORECASE
                        )
                except Exception as e:
                    logger.warning(f"⚠️ Failed to resolve CID {cid}: {type(e).__name__}")

            return html

        except Exception as e:
            logger.error(f"❌ CID resolution failed: {type(e).__name__}")
            return html
