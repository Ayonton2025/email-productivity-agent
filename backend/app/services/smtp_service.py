"""
SMTP Email Sending Service

Handles sending emails via SMTP and appending to Sent folder via IMAP.
"""

import asyncio
import logging
from typing import Tuple, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

import aiosmtplib
from imapclient import IMAPClient

from app.core.security import decrypt_credential
from app.models.database import UserEmailAccount, Email
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.services.hosted_email_abuse_service import HostedEmailAbuseService

logger = logging.getLogger(__name__)


class SMTPService:
    """SMTP email sending service"""

    def __init__(self):
        self.hosted_abuse_service = HostedEmailAbuseService()
    
    async def send_email(
        self,
        account: UserEmailAccount,
        db: AsyncSession,
        to: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        cc: Optional[list] = None,
        bcc: Optional[list] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[list] = None
    ) -> Tuple[bool, str]:
        """
        Send email via SMTP and append to Sent folder
        Returns: (success, message)
        """
        try:
            abuse_eval = None
            if getattr(account, "email_account_type", "external") == "hosted_internal":
                abuse_eval = await self.hosted_abuse_service.evaluate_send_permission(
                    session=db,
                    account=account,
                    to=to,
                    subject=subject,
                    body_text=body_text or "",
                )
                if not abuse_eval.get("allowed", False):
                    await self.hosted_abuse_service.record_send_attempt(
                        session=db,
                        account=account,
                        to=to,
                        subject=subject,
                        body_text=body_text or "",
                        blocked=True,
                        block_reason=abuse_eval.get("reason"),
                        spam_score=float(abuse_eval.get("spam_score") or 0.0),
                        ai_flagged=bool(abuse_eval.get("ai_flagged")),
                        link_count=int(abuse_eval.get("link_count") or 0),
                    )
                    return (False, f"❌ Send blocked: {abuse_eval.get('reason')}")

            password = decrypt_credential(account.encrypted_password)
            
            # Build email message
            if body_html:
                msg = MIMEMultipart('alternative')
                part1 = MIMEText(body_text, 'plain')
                part2 = MIMEText(body_html, 'html')
                msg.attach(part1)
                msg.attach(part2)
            else:
                msg = MIMEText(body_text, 'plain')
            
            # Set headers
            msg['From'] = account.email
            msg['To'] = to
            msg['Subject'] = subject
            
            if cc:
                msg['Cc'] = ', '.join(cc)
            
            if in_reply_to:
                msg['In-Reply-To'] = in_reply_to
            
            if references:
                msg['References'] = ' '.join(references)
            
            # Send via SMTP
            try:
                async with aiosmtplib.SMTP(
                    hostname=account.smtp_host,
                    port=account.smtp_port,
                    use_tls=account.use_tls
                ) as smtp:
                    await smtp.login(account.email, password)
                    await smtp.send_message(msg)
                
                logger.info(f"✅ Email sent from {account.email} to {to}")

                if getattr(account, "email_account_type", "external") == "hosted_internal":
                    await self.hosted_abuse_service.record_send_attempt(
                        session=db,
                        account=account,
                        to=to,
                        subject=subject,
                        body_text=body_text or "",
                        blocked=False,
                        block_reason=None,
                        spam_score=float((abuse_eval or {}).get("spam_score") or 0.0),
                        ai_flagged=bool((abuse_eval or {}).get("ai_flagged")),
                        link_count=int((abuse_eval or {}).get("link_count") or 0),
                    )
                
                # Append to Sent folder
                await self._append_to_sent(account, msg)
                
                return (True, "✅ Email sent successfully")
            
            except Exception as e:
                logger.error(f"SMTP send failed: {e}")
                if getattr(account, "email_account_type", "external") == "hosted_internal":
                    try:
                        await self.hosted_abuse_service.record_send_attempt(
                            session=db,
                            account=account,
                            to=to,
                            subject=subject,
                            body_text=body_text or "",
                            blocked=True,
                            block_reason=f"smtp_failure:{str(e)}",
                            spam_score=float((abuse_eval or {}).get("spam_score") or 0.0),
                            ai_flagged=bool((abuse_eval or {}).get("ai_flagged")),
                            link_count=int((abuse_eval or {}).get("link_count") or 0),
                        )
                    except Exception:
                        pass
                return (False, f"❌ Send failed: {str(e)}")
        
        except Exception as e:
            logger.error(f"Email sending error for {account.email}: {e}")
            return (False, f"❌ Error: {str(e)}")
    
    async def _append_to_sent(self, account: UserEmailAccount, msg: MIMEMultipart) -> bool:
        """Append sent email to Sent folder via IMAP"""
        try:
            password = decrypt_credential(account.encrypted_password)
            
            server = IMAPClient(
                account.imap_host,
                port=account.imap_port,
                use_uid=True,
                ssl=True
            )
            
            try:
                server.login(account.email, password)
                
                # Append to Sent folder
                # Gmail uses '[Gmail]/Sent Mail', others use 'Sent'
                sent_folder = 'Sent' if account.provider != 'gmail' else '[Gmail]/Sent Mail'
                
                try:
                    server.append(sent_folder, msg.as_bytes())
                    logger.info(f"✅ Email appended to {sent_folder}")
                    return True
                except:
                    # Try alternative Sent folder name
                    try:
                        server.append('Sent', msg.as_bytes())
                        logger.info("✅ Email appended to Sent")
                        return True
                    except:
                        logger.warning(f"Failed to append to Sent folder for {account.email}")
                        return False
            
            finally:
                server.logout()
        
        except Exception as e:
            logger.error(f"Failed to append to Sent for {account.email}: {e}")
            return False
    
    async def save_draft(
        self,
        account: UserEmailAccount,
        db: AsyncSession,
        to: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Save draft email
        Returns: (success, message, email_id)
        """
        try:
            # Create email record
            email = Email(
                account_id=account.id,
                user_id=account.user_id,
                message_id=f"draft-{datetime.utcnow().isoformat()}",
                uid=0,  # Drafts don't have IMAP UIDs yet
                sender=account.email,
                recipients=[to],
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                folder='Drafts',
                is_draft=True,
                processing_status='draft'
            )
            
            db.add(email)
            await db.commit()
            
            return (True, "✅ Draft saved", email.id)
        
        except Exception as e:
            logger.error(f"Failed to save draft: {e}")
            return (False, f"❌ Failed to save draft: {str(e)}", None)


# Global service instance
smtp_service = SMTPService()
