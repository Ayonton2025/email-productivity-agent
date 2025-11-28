import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.database import Email, EmailDraft
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService

class EmailService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_service = LLMService()
        self.prompt_service = PromptService(db)
    
    async def load_mock_emails(self, file_path: str, user_id: str = None) -> List[Dict[str, Any]]:
        """Load mock emails from JSON file"""
        try:
            with open(file_path, 'r') as f:
                emails_data = json.load(f)
            
            processed_emails = []
            for email_data in emails_data:
                processed_email = await self.process_single_email(email_data, user_id)
                processed_emails.append(processed_email)
            
            return processed_emails
        except Exception as e:
            print(f"Error loading mock emails: {e}")
            return []
    
    async def process_single_email(self, email_data: Dict[str, Any], user_id: str = None) -> Dict[str, Any]:
        """Process a single email with AI categorization and extraction"""
        
        # Get active prompts
        categorization_prompt = await self.prompt_service.get_active_prompt("categorization")
        action_prompt = await self.prompt_service.get_active_prompt("action_extraction")
        summary_prompt = await self.prompt_service.get_active_prompt("summary")
        
        email_content = f"From: {email_data.get('sender', '')}\nSubject: {email_data.get('subject', '')}\nBody: {email_data.get('body', '')}"
        
        # Run AI processing
        tasks = [
            self.llm_service.process_prompt(categorization_prompt.template, email_content),
            self.llm_service.process_prompt(action_prompt.template, email_content),
            self.llm_service.process_prompt(summary_prompt.template, email_content)
        ]
        
        category, action_items, summary = await asyncio.gather(*tasks)
        
        # Parse action items if it's JSON
        try:
            if action_items.strip().startswith('{') or action_items.strip().startswith('['):
                action_items_parsed = json.loads(action_items)
            else:
                action_items_parsed = [{"task": action_items, "deadline": None}]
        except:
            action_items_parsed = [{"task": action_items, "deadline": None}]
        
        # Create email record - ADD user_id field
        email = Email(
            user_id=user_id,  # CRITICAL: Add user_id to associate email with user
            sender=email_data.get('sender', ''),
            subject=email_data.get('subject', ''),
            body=email_data.get('body', ''),
            timestamp=datetime.fromisoformat(email_data.get('timestamp', datetime.utcnow().isoformat())),
            category=category,
            action_items=action_items_parsed,
            summary=summary,
            email_metadata=email_data.get('metadata', {})
        )
        
        self.db.add(email)
        await self.db.commit()
        await self.db.refresh(email)
        
        return email.to_dict()
    
    async def get_all_emails(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all emails with pagination"""
        try:
            result = await self.db.execute(
                select(Email).order_by(Email.timestamp.desc()).limit(limit).offset(offset)
            )
            emails = result.scalars().all()
            return [email.to_dict() for email in emails]
        except Exception as e:
            print(f"❌ [EmailService] Error in get_all_emails: {e}")
            return []
    
    async def get_user_emails(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get emails for a specific user"""
        try:
            print(f"📧 [EmailService] Getting emails for user: {user_id}")
            
            result = await self.db.execute(
                select(Email).where(Email.user_id == user_id)
                .order_by(Email.timestamp.desc())
                .limit(limit).offset(offset)
            )
            emails = result.scalars().all()
            
            print(f"📧 [EmailService] Found {len(emails)} emails in database")
            
            # Convert to dict and handle any serialization issues
            email_list = []
            for email in emails:
                try:
                    email_dict = email.to_dict()
                    email_list.append(email_dict)
                except Exception as e:
                    print(f"⚠️ [EmailService] Error converting email {email.id}: {e}")
                    # Create a basic dict as fallback
                    email_list.append({
                        "id": getattr(email, 'id', 'unknown'),
                        "user_id": getattr(email, 'user_id', 'unknown'),
                        "sender": getattr(email, 'sender', 'Unknown'),
                        "subject": getattr(email, 'subject', 'No Subject'),
                        "body": getattr(email, 'body', ''),
                        "timestamp": getattr(email, 'timestamp', '').isoformat() if getattr(email, 'timestamp', None) else '',
                        "category": getattr(email, 'category', 'Uncategorized')
                    })
            
            return email_list
            
        except Exception as e:
            print(f"❌ [EmailService] Error in get_user_emails: {e}")
            import traceback
            print(f"❌ [EmailService] Stack trace: {traceback.format_exc()}")
            return []
    
    async def get_email_by_id(self, email_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific email by ID"""
        try:
            result = await self.db.execute(select(Email).where(Email.id == email_id))
            email = result.scalar_one_or_none()
            return email.to_dict() if email else None
        except Exception as e:
            print(f"❌ [EmailService] Error getting email by ID: {e}")
            return None
    
    async def update_email_category(self, email_id: str, category: str) -> bool:
        """Update email category"""
        try:
            result = await self.db.execute(select(Email).where(Email.id == email_id))
            email = result.scalar_one_or_none()
            
            if email:
                email.category = category
                await self.db.commit()
                return True
            return False
        except Exception as e:
            print(f"❌ [EmailService] Error updating email category: {e}")
            return False
    
    async def create_draft(self, draft_data: Dict[str, Any], user_id: str = None) -> Dict[str, Any]:
        """Create a new email draft"""
        try:
            # CHANGED: Handle metadata field conversion
            draft_metadata = draft_data.pop('metadata', {})
            draft_data['draft_metadata'] = draft_metadata
            
            # Add user_id if provided
            if user_id:
                draft_data['user_id'] = user_id
                
            draft = EmailDraft(**draft_data)
            self.db.add(draft)
            await self.db.commit()
            await self.db.refresh(draft)
            return draft.to_dict()
        except Exception as e:
            print(f"❌ [EmailService] Error creating draft: {e}")
            raise
    
    async def get_drafts(self) -> List[Dict[str, Any]]:
        """Get all email drafts"""
        try:
            result = await self.db.execute(select(EmailDraft).order_by(EmailDraft.updated_at.desc()))
            drafts = result.scalars().all()
            return [draft.to_dict() for draft in drafts]
        except Exception as e:
            print(f"❌ [EmailService] Error getting drafts: {e}")
            return []
    
    async def get_user_drafts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get drafts for a specific user"""
        try:
            result = await self.db.execute(
                select(EmailDraft).where(EmailDraft.user_id == user_id)
                .order_by(EmailDraft.updated_at.desc())
            )
            drafts = result.scalars().all()
            return [draft.to_dict() for draft in drafts]
        except Exception as e:
            print(f"❌ [EmailService] Error getting user drafts: {e}")
            return []
    
    async def update_draft(self, draft_id: str, draft_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a draft"""
        try:
            result = await self.db.execute(select(EmailDraft).where(EmailDraft.id == draft_id))
            draft = result.scalar_one_or_none()
            
            if draft:
                for key, value in draft_data.items():
                    setattr(draft, key, value)
                await self.db.commit()
                await self.db.refresh(draft)
                return draft.to_dict()
            return None
        except Exception as e:
            print(f"❌ [EmailService] Error updating draft: {e}")
            return None
    
    async def delete_draft(self, draft_id: str) -> bool:
        """Delete a draft"""
        try:
            result = await self.db.execute(select(EmailDraft).where(EmailDraft.id == draft_id))
            draft = result.scalar_one_or_none()
            
            if draft:
                await self.db.delete(draft)
                await self.db.commit()
                return True
            return False
        except Exception as e:
            print(f"❌ [EmailService] Error deleting draft: {e}")
            return False
