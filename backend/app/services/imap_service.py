"""
IMAP Email Sync Service

Handles fetching emails from IMAP servers, parsing MIME, and storing in database.
Supports both IMAP IDLE (real-time) and polling modes.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from email import message_from_bytes
from email.header import decode_header
import logging

from imapclient import IMAPClient
from imapclient.exceptions import IMAPClientError

from app.core.config import settings
from app.core.security import decrypt_credential
from app.models.database import UserEmailAccount, Email, User
from app.services.email_ai_processing_service import process_emails_ai
from app.services.auto_reply_service import AutoReplyService
from app.services.email_attachment_integration import email_attachment_integration
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

# Import document analysis task handler (graceful fallback if not available)
try:
    from app.tasks.document_analysis_task import task_handler
    HAS_DOCUMENT_ANALYSIS = True
except ImportError:
    HAS_DOCUMENT_ANALYSIS = False
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ Document analysis tasks not available")

logger = logging.getLogger(__name__)


class IMAPService:
    """IMAP email sync service"""
    
    def __init__(self):
        self.active_connections: Dict[str, IMAPClient] = {}
    
    # ============== CONNECTION MANAGEMENT ==============
    
    async def test_connection(self, account: UserEmailAccount) -> Tuple[bool, str]:
        """
        Test IMAP connection without storing state
        Returns: (success, message)
        """
        try:
            password = decrypt_credential(account.encrypted_password)
            
            # Connect to IMAP
            server = IMAPClient(
                account.imap_host,
                port=account.imap_port,
                use_uid=True,
                ssl=True  # Gmail, Yahoo, Outlook all use SSL
            )
            
            # Try to login
            try:
                server.login(account.email, password)
                server.logout()
                return (True, f"✅ Successfully connected to {account.provider}")
            except IMAPClientError as e:
                return (False, f"❌ Login failed: {str(e)}")
            
        except Exception as e:
            logger.error(f"Connection test failed for {account.email}: {e}")
            return (False, f"❌ Connection error: {str(e)}")
    
    async def get_connection(self, account: UserEmailAccount) -> Optional[IMAPClient]:
        """Get or create IMAP connection"""
        try:
            password = decrypt_credential(account.encrypted_password)
            
            server = IMAPClient(
                account.imap_host,
                port=account.imap_port,
                use_uid=True,
                ssl=True
            )
            
            server.login(account.email, password)
            logger.info(f"✅ Connected to IMAP: {account.email}")
            return server
            
        except Exception as e:
            logger.error(f"Failed to connect to IMAP for {account.email}: {e}")
            return None
    
    # ============== EMAIL PARSING ==============
    
    def _decode_header(self, header_data: bytes) -> str:
        """Safely decode email header"""
        try:
            if isinstance(header_data, bytes):
                decoded_parts = []
                for text, encoding in decode_header(header_data):
                    if isinstance(text, bytes):
                        if encoding:
                            decoded_parts.append(text.decode(encoding, errors='ignore'))
                        else:
                            decoded_parts.append(text.decode('utf-8', errors='ignore'))
                    else:
                        decoded_parts.append(str(text))
                return ''.join(decoded_parts)
            return str(header_data)
        except:
            return str(header_data)
    
    def _parse_email(self, raw_email: bytes) -> Dict:
        """Parse raw MIME email into structured data"""
        try:
            msg = message_from_bytes(raw_email)
            
            # Extract headers
            sender = self._decode_header(msg.get('From', ''))
            subject = self._decode_header(msg.get('Subject', ''))
            message_id = msg.get('Message-ID', '').strip('<>')
            received_at_str = msg.get('Date', datetime.utcnow().isoformat())
            
            # Parse recipients
            to = msg.get('To', '')
            cc = msg.get('Cc', '')
            bcc = msg.get('Bcc', '')
            
            recipients = [self._decode_header(to)] if to else []
            cc_list = [self._decode_header(cc)] if cc else []
            bcc_list = [self._decode_header(bcc)] if bcc else []
            
            # Extract body
            body_text = ""
            body_html = ""
            attachments = []
            
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = part.get('Content-Disposition', '')
                    
                    if 'attachment' in content_disposition:
                        filename = part.get_filename()
                        if filename:
                            attachments.append({
                                'filename': self._decode_header(filename),
                                'content_type': content_type,
                                'size': len(part.get_payload(decode=True))
                            })
                    
                    elif content_type == 'text/plain' and not body_text:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset('utf-8')
                        if payload:
                            body_text = payload.decode(charset, errors='ignore')
                    
                    elif content_type == 'text/html' and not body_html:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset('utf-8')
                        if payload:
                            body_html = payload.decode(charset, errors='ignore')
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset('utf-8')
                    body_text = payload.decode(charset, errors='ignore')
            
            # Parse received date
            try:
                from email.utils import parsedate_to_datetime
                received_at = parsedate_to_datetime(received_at_str)
            except:
                received_at = datetime.utcnow()
            if received_at.tzinfo is None:
                received_at = received_at.replace(tzinfo=timezone.utc)
            received_at = received_at.astimezone(timezone.utc).replace(tzinfo=None)
            
            return {
                'message_id': message_id,
                'sender': sender,
                'subject': subject,
                'recipients': recipients,
                'cc': cc_list,
                'bcc': bcc_list,
                'body_text': body_text,
                'body_html': body_html,
                'attachments': attachments,
                'received_at': received_at,
                'raw_mime': raw_email.decode('utf-8', errors='ignore')
            }
        except Exception as e:
            logger.error(f"Error parsing email: {e}")
            return None
    
    # ============== EMAIL SYNC ==============
    
    async def sync_inbox(self, account: UserEmailAccount, db: AsyncSession, limit: int = 100) -> Tuple[int, str]:
        """
        Full sync of inbox emails
        Returns: (emails_synced, status_message)
        """
        try:
            server = await self.get_connection(account)
            if not server:
                return (0, "Failed to connect to IMAP")
            
            try:
                # Select INBOX
                server.select_folder('INBOX')
                
                # Search for all emails
                uids = server.search(['ALL'])
                logger.info(f"Found {len(uids)} emails in INBOX for {account.email}")
                
                # Limit to recent emails
                uids = list(reversed(uids))[-limit:]
                
                emails_synced = 0
                new_email_ids: List[str] = []
                
                for uid in uids:
                    try:
                        # Fetch email
                        raw_email = server.fetch(uid, ['RFC822'])[uid][b'RFC822']
                        
                        # Parse email
                        parsed = self._parse_email(raw_email)
                        if not parsed:
                            continue
                        
                        # Check if already exists
                        stmt = select(Email).where(
                            and_(
                                Email.account_id == account.id,
                                Email.message_id == parsed['message_id']
                            )
                        )
                        existing = await db.execute(stmt)
                        if existing.scalar_one_or_none():
                            continue
                        
                        # Create email record
                        email = Email(
                            account_id=account.id,
                            user_id=account.user_id,
                            uid=uid,
                            message_id=parsed['message_id'],
                            sender=parsed['sender'],
                            recipients=parsed['recipients'],
                            cc=parsed['cc'],
                            bcc=parsed['bcc'],
                            subject=parsed['subject'],
                            body_text=parsed['body_text'],
                            body_html=parsed['body_html'],
                            attachments=parsed['attachments'],
                            received_at=parsed['received_at'],
                            folder='INBOX',
                            raw_mime=parsed['raw_mime'],
                            processing_status='pending'
                        )
                        
                        db.add(email)
                        await db.flush()  # Get email.id without committing
                        
                        # Process attachments for this email
                        attachments_metadata = parsed.get('attachments', [])
                        if attachments_metadata:
                            try:
                                await email_attachment_integration.process_imap_attachments(
                                    email.id,
                                    account.user_id,
                                    attachments_metadata,
                                    raw_email,
                                    db
                                )
                                logger.info(f"✅ Processed IMAP attachments for: {parsed['subject']}")
                                
                                # Trigger document analysis for attachments
                                if HAS_DOCUMENT_ANALYSIS:
                                    try:
                                        user_plan = "free"  # Default plan
                                        user_result = await db.execute(
                                            select(User).where(User.id == account.user_id)
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
                                            user_id=account.user_id,
                                            user_plan=user_plan
                                        )
                                        logger.info(f"📊 Queued document analysis for IMAP email: {email.id}")
                                    except Exception as e:
                                        logger.warning(f"⚠️ Could not queue IMAP attachment analysis: {e}")
                                        # Don't fail email sync if analysis queueing fails
                            except Exception as e:
                                logger.error(f"⚠️ Failed to process IMAP attachments for {parsed['subject']}: {e}")
                                # Don't fail the whole sync if attachments fail
                        
                        emails_synced += 1
                        new_email_ids.append(email.id)
                    
                    except Exception as e:
                        logger.error(f"Error syncing email UID {uid}: {e}")
                        continue
                
                await db.commit()
                account.last_sync = datetime.utcnow()
                account.last_sync_status = 'success'
                account.total_emails = emails_synced
                await db.commit()

                # AI processing (best-effort)
                try:
                    await process_emails_ai(db, new_email_ids)
                except Exception:
                    pass

                # Auto-reply (best-effort)
                try:
                    ar = AutoReplyService(db)
                    for eid in new_email_ids:
                        stmt = select(Email).where(Email.id == eid)
                        res = await db.execute(stmt)
                        row = res.scalar_one_or_none()
                        if not row:
                            continue
                        d = row.to_dict()
                        d["references"] = getattr(row, "references", None) or []
                        await ar.process_email_for_auto_reply(
                            d, account.user_id,
                            account_id=str(account.id),
                            account_provider=account.provider or "imap",
                        )
                except Exception:
                    pass

                return (emails_synced, f"✅ Synced {emails_synced} emails")
            
            finally:
                server.logout()
        
        except Exception as e:
            logger.error(f"Sync failed for {account.email}: {e}")
            account.last_sync_status = 'failed'
            account.sync_error = str(e)
            await db.commit()
            return (0, f"❌ Sync failed: {str(e)}")
    
    async def get_folder_list(self, account: UserEmailAccount) -> List[str]:
        """Get list of folders in mailbox"""
        try:
            server = await self.get_connection(account)
            if not server:
                return []
            
            try:
                folders = server.list_folders()
                folder_names = [f[2] for f in folders]
                return folder_names
            finally:
                server.logout()
        except Exception as e:
            logger.error(f"Failed to get folders for {account.email}: {e}")
            return []
    
    async def fetch_folder_emails(self, account: UserEmailAccount, db: AsyncSession, folder: str = 'INBOX', limit: int = 50) -> List[Dict]:
        """Fetch emails from specific folder"""
        try:
            server = await self.get_connection(account)
            if not server:
                return []
            
            try:
                server.select_folder(folder)
                uids = list(reversed(server.search(['ALL'])))[-limit:]
                
                emails = []
                for uid in uids:
                    try:
                        raw_email = server.fetch(uid, ['RFC822'])[uid][b'RFC822']
                        parsed = self._parse_email(raw_email)
                        if parsed:
                            emails.append(parsed)
                    except:
                        continue
                
                return emails
            finally:
                server.logout()
        except Exception as e:
            logger.error(f"Failed to fetch folder {folder} for {account.email}: {e}")
            return []


# Global service instance
imap_service = IMAPService()
