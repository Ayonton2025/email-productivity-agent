"""
Email Sync Integration with Attachment Extraction
Handles automatic extraction and storage of email attachments during sync
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_models import EmailAttachment
from app.services.attachment_service import AttachmentService

logger = logging.getLogger(__name__)


class EmailAttachmentIntegration:
    """Integrates attachment extraction with email sync process"""
    
    def __init__(self):
        self.attachment_service = AttachmentService()
    
    async def process_gmail_attachments(
        self,
        service,
        message_id: str,
        email_id: str,
        user_id: str,
        attachments_metadata: List[Dict[str, Any]],
        db: AsyncSession
    ) -> List[EmailAttachment]:
        """
        Download and store attachments for a Gmail message
        
        Args:
            service: Gmail API service
            message_id: Gmail message ID
            email_id: Database email ID
            user_id: User ID
            attachments_metadata: Attachment metadata from parse_gmail_message
            db: Database session
        
        Returns:
            List of stored EmailAttachment records
        """
        stored_attachments = []
        
        if not attachments_metadata:
            return stored_attachments
        
        try:
            for att_meta in attachments_metadata:
                attachment_id = att_meta.get("attachment_id")
                filename = att_meta.get("filename")
                mime_type = att_meta.get("mime_type")
                
                if not attachment_id or not filename:
                    logger.warning(f"Skipping attachment without ID or filename")
                    continue
                
                try:
                    # Download attachment from Gmail
                    att_data = service.users().messages().attachments().get(
                        userId="me",
                        messageId=message_id,
                        id=attachment_id
                    ).execute()
                    
                    # Decode file content
                    import base64
                    file_content = base64.urlsafe_b64decode(att_data.get("data", ""))
                    
                    if not file_content:
                        logger.warning(f"No content for attachment: {filename}")
                        continue
                    
                    # Store attachment
                    attachment_record = await self.attachment_service.store_attachment(
                        db,
                        email_id,
                        user_id,
                        filename,
                        mime_type,
                        file_content
                    )
                    
                    if attachment_record:
                        stored_attachments.append(attachment_record)
                        logger.info(f"✅ Stored Gmail attachment: {filename} ({len(file_content)} bytes)")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to download Gmail attachment {filename}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"❌ Error processing Gmail attachments: {e}")
        
        return stored_attachments
    
    async def process_imap_attachments(
        self,
        email_id: str,
        user_id: str,
        attachments_metadata: List[Dict[str, Any]],
        raw_email_bytes: bytes,
        db: AsyncSession
    ) -> List[EmailAttachment]:
        """
        Extract and store attachments from IMAP email
        
        Args:
            email_id: Database email ID
            user_id: User ID
            attachments_metadata: Attachment metadata from IMAP parsing
            raw_email_bytes: Raw MIME email bytes
            db: Database session
        
        Returns:
            List of stored EmailAttachment records
        """
        stored_attachments = []
        
        if not attachments_metadata:
            return stored_attachments
        
        try:
            from email import message_from_bytes
            
            # Parse the raw email to extract attachment content
            msg = message_from_bytes(raw_email_bytes)
            
            for part in msg.walk():
                content_disposition = part.get('Content-Disposition', '')
                
                if 'attachment' in content_disposition:
                    filename = part.get_filename()
                    if not filename:
                        continue
                    
                    try:
                        # Get file content
                        file_content = part.get_payload(decode=True)
                        
                        if not file_content:
                            logger.warning(f"No content for IMAP attachment: {filename}")
                            continue
                        
                        mime_type = part.get_content_type()
                        
                        # Store attachment
                        attachment_record = await self.attachment_service.store_attachment(
                            db,
                            email_id,
                            user_id,
                            filename,
                            mime_type,
                            file_content
                        )
                        
                        if attachment_record:
                            stored_attachments.append(attachment_record)
                            logger.info(f"✅ Stored IMAP attachment: {filename} ({len(file_content)} bytes)")
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to extract IMAP attachment {filename}: {e}")
                        continue
            
        except Exception as e:
            logger.error(f"❌ Error processing IMAP attachments: {e}")
        
        return stored_attachments


# Global integration instance
email_attachment_integration = EmailAttachmentIntegration()
