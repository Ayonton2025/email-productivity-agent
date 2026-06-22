"""
Webhook Handlers for Email Provider Push Notifications

Handles Gmail push notifications from Google Pub/Sub
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime
import logging
import json
import base64

from app.models.database import get_db, UserEmailAccount, Email
from app.services.gmail_ingestion_service import GmailIngestionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/gmail")
async def gmail_push_notification(
    body: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle incoming Gmail push notifications from Google Pub/Sub.
    
    When Gmail watch is active, Google sends notifications about new/updated emails.
    This endpoint receives those notifications and triggers incremental sync.
    
    Expected payload format:
    {
        "message": {
            "data": "<base64-encoded-data>",
            "messageId": "...",
            "publishTime": "..."
        },
        "subscription": "..."
    }
    """
    try:
        logger.info(f"📢 Received Gmail push notification")
        
        # Extract message data
        if "message" not in body or "data" not in body["message"]:
            logger.warning("⚠️ Invalid Gmail push payload")
            return {"success": False, "error": "Invalid payload"}
        
        # Decode base64 data
        message_data = body["message"]["data"]
        decoded = base64.b64decode(message_data).decode("utf-8")
        data = json.loads(decoded)
        
        history_id = data.get("historyId")
        email_address = data.get("emailAddress")
        
        logger.info(f"📧 Gmail push: historyId={history_id}, email={email_address}")
        
        if not history_id or not email_address:
            logger.warning("⚠️ Missing historyId or email in push data")
            return {"success": False, "error": "Missing required fields"}
        
        # Schedule background sync
        background_tasks.add_task(
            handle_gmail_sync,
            email_address,
            history_id,
            db
        )
        
        return {
            "success": True,
            "message": "Push notification received, sync scheduled"
        }
    
    except Exception as e:
        logger.error(f"❌ Error processing Gmail push: {e}")
        return {"success": False, "error": str(e)}


async def handle_gmail_sync(
    email_address: str,
    history_id: str,
    db: AsyncSession
):
    """
    Handle incremental email sync based on Gmail push notification.
    
    This fetches only NEW emails since the last historyId.
    """
    try:
        logger.info(f"🔄 Starting incremental Gmail sync for {email_address}")
        
        # Find the account
        result = await db.execute(
            select(UserEmailAccount).where(
                UserEmailAccount.email == email_address
            )
        )
        account = result.scalar_one_or_none()
        
        if not account:
            logger.warning(f"⚠️ No account found for {email_address}")
            return
        
        # Check if we have access token
        if not account.access_token:
            logger.warning(f"⚠️ No access token for {email_address}, skipping sync")
            return
        
        # Decrypt the token
        from app.core.security import decrypt_credential
        access_token = decrypt_credential(account.access_token)
        
        # Create ingestion service
        ingestion_service = GmailIngestionService(db)
        service = ingestion_service.build_gmail_service(access_token)
        
        # Fetch new messages since last historyId
        try:
            logger.info(f"📧 Fetching emails since historyId {account.history_id or '(first sync)'}")
            
            # If this is the first incremental sync, fetch last 10 emails
            if not account.history_id:
                raw_emails = await ingestion_service.fetch_last_n_emails(service, n=10)
            else:
                # Use Gmail History API to get only changed messages
                history_result = service.users().history().list(
                    userId="me",
                    startHistoryId=account.history_id,
                    historyTypes=["messageAdded", "messageDeleted"]
                ).execute()
                
                changes = history_result.get("history", [])
                message_ids = []
                
                for change in changes:
                    if "messagesAdded" in change:
                        for msg in change["messagesAdded"]:
                            message_ids.append(msg["message"]["id"])
                
                if not message_ids:
                    logger.info("✅ No new messages since last sync")
                    return
                
                # Fetch full messages
                raw_emails = []
                for msg_id in message_ids[:20]:  # Limit to 20 per push
                    try:
                        full = service.users().messages().get(
                            userId="me",
                            id=msg_id,
                            format="full"
                        ).execute()
                        raw_emails.append(full)
                    except Exception as e:
                        logger.error(f"❌ Failed to fetch message {msg_id}: {e}")
                        continue
            
            logger.info(f"📧 Fetched {len(raw_emails)} new emails")
            
            # Parse and store with attachment extraction
            parsed_emails = [ingestion_service.parse_gmail_message(msg) for msg in raw_emails]
            email_ids = await ingestion_service.store_emails(
                user_id=account.user_id,
                account_id=account.id,
                parsed_emails=parsed_emails,
                gmail_service=service,  # Pass Gmail service for attachment download
                message_ids=message_ids[:len(raw_emails)]  # Pass message IDs for attachment extraction
            )
            
            logger.info(f"✅ Stored {len(email_ids)} new emails")
            
            # Process with AI
            if email_ids:
                processed_count = await ingestion_service.process_emails_with_ai(email_ids)
                logger.info(f"✅ AI processing completed for {processed_count} emails")
            
            # Update account history_id and last_sync
            account.history_id = history_id
            account.last_sync = datetime.utcnow()
            account.last_sync_status = "success"
            await db.commit()
            
            logger.info(f"✅ Incremental sync completed for {email_address}")
        
        except Exception as e:
            logger.error(f"❌ Sync failed: {e}")
            account.last_sync_status = "failed"
            account.sync_error = str(e)
            await db.commit()
            raise
    
    except Exception as e:
        logger.error(f"❌ Error in handle_gmail_sync: {e}")
