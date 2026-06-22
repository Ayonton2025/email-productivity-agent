"""
Gmail Email Ingestion Service

Handles:
- Fetching emails from Gmail via Google API
- Parsing email messages with proper MIME handling
- HTML content extraction and sanitization
- Inline image (CID) resolution
- Storing emails in the database
- AI categorization pipeline
- Push notification setup
"""

import base64
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
import html

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth import exceptions
from googleapiclient.discovery import build

from app.models.database import Email, UserEmailAccount, User
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService
from app.services.email_attachment_integration import email_attachment_integration

# Import document analysis task handler (graceful fallback if not available)
try:
    from app.tasks.document_analysis_task import task_handler
    HAS_DOCUMENT_ANALYSIS = True
except ImportError:
    HAS_DOCUMENT_ANALYSIS = False
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ Document analysis tasks not available")

# Try to import bleach for HTML sanitization; if not available, use basic sanitization
try:
    from bleach import clean as bleach_clean  # type: ignore[import]
    HAS_BLEACH = True
except ImportError:
    HAS_BLEACH = False
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ bleach not installed, using basic HTML sanitization")

logger = logging.getLogger(__name__)


class GmailIngestionService:
    """Service for ingesting emails from Gmail"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_service = LLMService()
        self.prompt_service = PromptService(db)
    
    def build_gmail_service(self, access_token: str):
        """Build Gmail service with OAuth credentials"""
        credentials = Credentials(token=access_token)
        return build("gmail", "v1", credentials=credentials)
    
    async def fetch_last_n_emails(
        self,
        service,
        n: int = 50,
        query: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Fetch the last N emails from Gmail.
        
        Args:
            service: Gmail API service
            n: Number of emails to fetch
            query: Gmail search query (optional)
        
        Returns:
            List of parsed email dictionaries
        """
        try:
            logger.info(f"📧 Fetching last {n} emails from Gmail...")
            
            # Get message IDs
            results = service.users().messages().list(
                userId="me",
                maxResults=min(n, 50),  # Gmail API max is 100, we use 50 per request
                q=query if query else None
            ).execute()
            
            messages = results.get("messages", [])
            logger.info(f"📧 Found {len(messages)} message IDs")
            
            if not messages:
                logger.warning("⚠️ No messages found")
                return []
            
            # Fetch full message details
            full_emails = []
            for msg in messages:
                try:
                    full = service.users().messages().get(
                        userId="me",
                        id=msg["id"],
                        format="full"
                    ).execute()
                    full_emails.append(full)
                except Exception as e:
                    logger.error(f"❌ Failed to fetch message {msg['id']}: {e}")
                    continue
            
            logger.info(f"✅ Successfully fetched {len(full_emails)} full messages")
            return full_emails
        
        except Exception as e:
            logger.error(f"❌ Error fetching emails: {e}")
            raise
    
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
            body_html, body_text = self._extract_body(message["payload"])
            
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
            logger.error(f"❌ Error parsing message: {e}")
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
                    attachments.append({
                        "filename": part["filename"],
                        "mime_type": part.get("mimeType", ""),
                        "size": part.get("body", {}).get("size", 0),
                        "attachment_id": part.get("body", {}).get("attachmentId", "")
                    })
                
                # Check nested parts
                if "parts" in part:
                    process_parts(part["parts"])
        
        if "parts" in payload:
            process_parts(payload["parts"])
        
        return attachments
    
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
                    'a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol', 'p',
                    'pre', 'strong', 'ul', 'br', 'div', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                    'img', 'table', 'tr', 'td', 'th', 'thead', 'tbody', 'tfoot'
                ]
                
                allowed_attributes = {
                    '*': ['style', 'class'],
                    'a': ['href', 'target', 'rel', 'title'],
                    'img': ['src', 'alt', 'width', 'height', 'style', 'loading'],
                    'table': ['border', 'cellpadding', 'cellspacing', 'style'],
                    'td': ['colspan', 'rowspan', 'style'],
                    'th': ['colspan', 'rowspan', 'style'],
                }
                
                # Sanitize with bleach
                sanitized = bleach_clean(
                    html,
                    tags=allowed_tags,
                    attributes=allowed_attributes,
                    strip=True
                )
                
                # Ensure links open in new tab
                sanitized = re.sub(
                    r'<a\s+(?!target=)',
                    '<a target="_blank" rel="noopener noreferrer" ',
                    sanitized
                )
                
                return sanitized
            else:
                # Fallback: basic HTML sanitization
                logger.debug("Using basic HTML sanitization (bleach not available)")
                
                # Remove script tags
                html = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', html, flags=re.DOTALL | re.IGNORECASE)
                # Remove style tags (but keep content style attributes)
                html = re.sub(r'<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>', '', html, flags=re.DOTALL | re.IGNORECASE)
                # Remove event handlers
                html = re.sub(r'\s*on\w+=\s*["\']?[^"\']*["\']?', '', html, flags=re.IGNORECASE)
                
                return html
        
        except Exception as e:
            logger.error(f"❌ HTML sanitization failed: {e}")
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
                    f'cid:{cid}',
                    f'cid:{re.escape(cid)}',
                ]
                
                # Get attachment content as base64
                try:
                    mime_type = att.get("mime_type", "image/png")
                    # Note: Gmail API returns attachment content via separate API call
                    # For now, we'll use a placeholder and note this needs attachment download
                    data_uri = f'data:{mime_type};base64,[ATTACHMENT_DATA]'
                    
                    for pattern in patterns:
                        html = re.sub(
                            f'src=(["\'])' + re.escape(pattern),
                            f'src=\\1{data_uri}',
                            html,
                            flags=re.IGNORECASE
                        )
                except Exception as e:
                    logger.warning(f"⚠️ Failed to resolve CID {cid}: {e}")
            
            return html
        
        except Exception as e:
            logger.error(f"❌ CID resolution failed: {e}")
            return html
    
    async def store_emails(
        self,
        user_id: str,
        account_id: str,
        parsed_emails: List[Dict[str, Any]],
        gmail_service=None,
        message_ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Store parsed emails in the database and extract attachments
        
        Args:
            user_id: User ID
            account_id: Email account ID
            parsed_emails: List of parsed email dictionaries
            gmail_service: Optional Gmail API service for attachment download
            message_ids: Optional list of Gmail message IDs for attachment download
        
        Returns:
            List of stored email IDs
        """
        try:
            stored_ids = []
            
            for idx, parsed_email in enumerate(parsed_emails):
                # Check if email already exists
                result = await self.db.execute(
                    select(Email).where(
                        Email.message_id == parsed_email["message_id"]
                    )
                )
                
                if result.scalar_one_or_none():
                    logger.debug(f"📧 Email {parsed_email['message_id']} already exists, skipping")
                    continue
                
                # Create email record
                email = Email(
                    user_id=user_id,
                    account_id=account_id,
                    message_id=parsed_email["message_id"],
                    uid=int(parsed_email["external_id"][:20].replace("-", "")[:19]) or 0,  # Use timestamp portion
                    sender=parsed_email["sender"],
                    recipients=parsed_email.get("recipients", []),
                    cc=parsed_email.get("cc", []),
                    subject=parsed_email["subject"],
                    body_text=parsed_email.get("body_text", ""),
                    body_html=parsed_email.get("body_html", ""),
                    received_at=parsed_email["received_at"],
                    is_read=parsed_email.get("is_read", False),
                    is_flagged=parsed_email.get("is_flagged", False),
                    is_spam=parsed_email.get("is_spam", False),
                    is_draft=parsed_email.get("is_draft", False),
                    thread_id=parsed_email.get("thread_id"),
                    attachments=parsed_email.get("attachments", []),
                    processing_status="pending",  # Will be AI-processed next
                )
                
                self.db.add(email)
                await self.db.flush()  # Get email.id without committing
                
                # Process attachments if Gmail service is provided
                if gmail_service and message_ids and idx < len(message_ids):
                    attachments_metadata = parsed_email.get("attachments", [])
                    gmail_message_id = message_ids[idx]
                    
                    if attachments_metadata:
                        try:
                            await email_attachment_integration.process_gmail_attachments(
                                gmail_service,
                                gmail_message_id,
                                email.id,
                                user_id,
                                attachments_metadata,
                                self.db
                            )
                            logger.info(f"✅ Processed attachments for email: {parsed_email['subject']}")
                            
                            # Trigger document analysis for attachments
                            if HAS_DOCUMENT_ANALYSIS:
                                try:
                                    # Get user's plan for tiered analysis
                                    user_plan = "free"  # Default plan
                                    user_result = await self.db.execute(
                                        select(User).where(User.id == user_id)
                                    )
                                    user = user_result.scalars().first()
                                    if user:
                                        if getattr(user, "subscription_status", "free") == "active":
                                            user_plan = getattr(user, "plan", "pro") or "pro"
                                        elif (getattr(user, "plan", "") or "").lower() in {"pro", "plus", "professional", "enterprise"}:
                                            user_plan = user.plan
                                    
                                    # Queue analysis for this email's attachments
                                    await task_handler.analyze_email_attachments(
                                        email_id=email.id,
                                        user_id=user_id,
                                        user_plan=user_plan
                                    )
                                    logger.info(f"📊 Queued document analysis for email: {email.id}")
                                except Exception as e:
                                    logger.warning(f"⚠️ Could not queue attachment analysis: {e}")
                                    # Don't fail email sync if analysis queueing fails
                        except Exception as e:
                            logger.error(f"⚠️ Failed to process attachments for {parsed_email['subject']}: {e}")
                            # Don't fail the whole email sync if attachments fail
                
                stored_ids.append(email.id)
            
            if stored_ids:
                await self.db.commit()
                logger.info(f"✅ Stored {len(stored_ids)} new emails with attachments")
            
            return stored_ids
        
        except Exception as e:
            logger.error(f"❌ Error storing emails: {e}")
            await self.db.rollback()
            raise
    
    async def process_emails_with_ai(
        self,
        email_ids: List[str]
    ) -> int:
        """
        Run AI categorization on emails.
        
        Args:
            email_ids: List of email IDs to process
        
        Returns:
            Number of successfully processed emails
        """
        try:
            processed_count = 0
            
            # Get active prompts
            categorization_prompt = await self.prompt_service.get_active_prompt("categorization")
            summary_prompt = await self.prompt_service.get_active_prompt("summary")
            
            if not categorization_prompt or not summary_prompt:
                logger.warning("⚠️ AI prompts not found, skipping AI processing")
                return 0
            
            for email_id in email_ids:
                try:
                    # Fetch email
                    result = await self.db.execute(
                        select(Email).where(Email.id == email_id)
                    )
                    email = result.scalar_one_or_none()
                    
                    if not email:
                        logger.warning(f"⚠️ Email {email_id} not found")
                        continue
                    
                    # Skip if already processed
                    if email.processing_status == "completed":
                        continue
                    
                    # Prepare content for AI
                    email_content = f"From: {email.sender}\nSubject: {email.subject}\nBody: {email.body_text or email.body_html}"
                    
                    # Categorize
                    try:
                        category = await self.llm_service.process_prompt(
                            categorization_prompt.template,
                            email_content,
                            max_tokens=50
                        )
                        email.ai_category = category.strip()
                    except Exception as e:
                        logger.error(f"❌ Categorization failed for {email_id}: {e}")
                        email.ai_category = "Uncategorized"
                    
                    # Summarize
                    try:
                        summary = await self.llm_service.process_prompt(
                            summary_prompt.template,
                            email_content,
                            max_tokens=150
                        )
                        email.ai_summary = summary.strip()
                    except Exception as e:
                        logger.error(f"❌ Summarization failed for {email_id}: {e}")
                    
                    email.processing_status = "completed"
                    processed_count += 1
                    logger.debug(f"✅ Processed email {email_id}: {email.ai_category}")
                
                except Exception as e:
                    logger.error(f"❌ Error processing email {email_id}: {e}")
                    email.processing_status = "failed"
                    continue
            
            if processed_count > 0:
                await self.db.commit()
                logger.info(f"✅ AI processing completed for {processed_count} emails")
            
            return processed_count
        
        except Exception as e:
            logger.error(f"❌ Error in AI processing pipeline: {e}")
            await self.db.rollback()
            raise
    
    async def setup_gmail_push(
        self,
        service,
        account: UserEmailAccount,
        topic_name: str
    ) -> bool:
        """
        Setup Gmail push notifications via Google Pub/Sub.
        
        Args:
            service: Gmail API service
            account: UserEmailAccount record
            topic_name: Google Pub/Sub topic name
        
        Returns:
            True if successful
        """
        try:
            logger.info(f"📢 Setting up Gmail push notifications for {account.email}")
            
            response = service.users().watch(
                userId="me",
                body={
                    "topicName": topic_name,
                    "labelIds": ["INBOX"]  # Watch INBOX label
                }
            ).execute()
            
            account.history_id = response.get("historyId")
            account.watch_expiration = datetime.utcfromtimestamp(
                int(response.get("expiration", 0)) / 1000
            )
            
            await self.db.commit()
            logger.info(f"✅ Gmail watch enabled. History ID: {account.history_id}")
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to setup Gmail push: {e}")
            return False
