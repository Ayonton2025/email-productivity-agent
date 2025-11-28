# backend/app/services/email_service.py
import json
import asyncio
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.database import Email, EmailDraft
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService
from app.core.config import settings

class EmailService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_service = LLMService()
        self.prompt_service = PromptService(db)
    
    async def load_mock_emails(self, user_id: str) -> List[Dict[str, Any]]:
        """Load mock emails from JSON file into database for a specific user"""
        try:
            print(f"📧 [EmailService] Loading mock emails for user: {user_id}")
            
            # First, check if user already has emails to avoid duplicates
            existing_emails = await self.get_user_emails(user_id)
            if existing_emails:
                print(f"📧 [EmailService] User already has {len(existing_emails)} emails, skipping mock load")
                return existing_emails
            
            # Load mock data from file
            file_path = settings.MOCK_DATA_PATH
            if not os.path.exists(file_path):
                print(f"❌ [EmailService] Mock data file not found: {file_path}")
                # Use hardcoded mock data as fallback
                mock_emails = self._get_hardcoded_mock_emails()
            else:
                with open(file_path, 'r') as f:
                    mock_emails = json.load(f)
            
            print(f"📧 [EmailService] Found {len(mock_emails)} mock emails to load")
            
            processed_emails = []
            for email_data in mock_emails:
                processed_email = await self.process_single_email(email_data, user_id)
                processed_emails.append(processed_email)
            
            print(f"✅ [EmailService] Successfully loaded {len(processed_emails)} mock emails")
            return processed_emails
            
        except Exception as e:
            print(f"❌ [EmailService] Error loading mock emails: {e}")
            import traceback
            print(f"❌ [EmailService] Stack trace: {traceback.format_exc()}")
            return []
    
    def _get_hardcoded_mock_emails(self) -> List[Dict[str, Any]]:
        """Fallback hardcoded mock emails if JSON file is missing"""
        return [
            {
                "id": "1",
                "sender": "project.manager@company.com",
                "subject": "Q4 Project Review Meeting",
                "body": "Hi team, We need to schedule the Q4 project review meeting for next week. Please review the attached project report and come prepared to discuss milestones, challenges, and next quarter planning. The meeting should take about 2 hours. Let me know your availability for Tuesday or Wednesday.",
                "timestamp": "2024-01-08T10:30:00Z",
                "category": "Important",
                "priority": "high",
                "is_read": False,
                "is_archived": False,
                "is_starred": False,
                "action_items": [
                    {"task": "Review project report", "deadline": "2024-01-12", "priority": "high"},
                    {"task": "Prepare milestone updates", "deadline": "2024-01-12", "priority": "medium"}
                ],
                "summary": "Meeting request for Q4 project review with attached report",
                "metadata": {"type": "meeting_request", "duration": "2 hours"}
            },
            {
                "id": "2", 
                "sender": "ceo@company.com",
                "subject": "Urgent: All-Hands Meeting Tomorrow",
                "body": "Team, We need to have an all-hands meeting tomorrow at 10 AM to discuss the recent market developments. This is mandatory for all department heads. Please clear your schedules.",
                "timestamp": "2024-01-07T16:45:00Z",
                "category": "Important",
                "priority": "high",
                "is_read": False,
                "is_archived": False,
                "is_starred": False,
                "action_items": [
                    {"task": "Attend all-hands meeting", "deadline": "2024-01-09", "priority": "high"}
                ],
                "summary": "Mandatory all-hands meeting about market developments",
                "metadata": {"type": "meeting_request", "mandatory": True}
            },
            # Add more emails as needed for testing
            {
                "id": "17",
                "sender": "project.updates@company.com", 
                "subject": "Project Phoenix: Phase 2 Completed",
                "body": "Great news! Phase 2 of Project Phoenix has been completed ahead of schedule. Key achievements: - All milestones met - Budget maintained - Client satisfaction high. Phase 3 planning begins next week.",
                "timestamp": "2024-01-08T13:45:00Z",
                "category": "Important",
                "priority": "medium", 
                "is_read": False,
                "is_archived": False,
                "is_starred": False,
                "action_items": [
                    {"task": "Review Phase 2 completion report", "deadline": "2024-01-15", "priority": "low"}
                ],
                "summary": "Project Phoenix Phase 2 completed successfully ahead of schedule",
                "metadata": {"type": "project_update", "status": "completed"}
            }
        ]
    
    async def process_single_email(self, email_data: Dict[str, Any], user_id: str = None) -> Dict[str, Any]:
        """Process a single email and save to database"""
        try:
            print(f"📧 [EmailService] Processing email: {email_data.get('subject', 'No Subject')}")
            
            # Handle timestamp conversion
            raw_ts = email_data.get('timestamp', datetime.utcnow().isoformat())
            if isinstance(raw_ts, str) and raw_ts.endswith('Z'):
                raw_ts = raw_ts.replace('Z', '+00:00')
            timestamp = datetime.fromisoformat(raw_ts)
            
            # Use existing AI-generated data or generate new
            category = email_data.get('category', 'Uncategorized')
            action_items = email_data.get('action_items', [])
            summary = email_data.get('summary', '')
            
            # If we have an LLM service and want to regenerate AI data
            if self.llm_service and not category:
                try:
                    categorization_prompt = await self.prompt_service.get_active_prompt("categorization")
                    action_prompt = await self.prompt_service.get_active_prompt("action_extraction")
                    summary_prompt = await self.prompt_service.get_active_prompt("summary")
                    
                    email_content = f"From: {email_data.get('sender', '')}\nSubject: {email_data.get('subject', '')}\nBody: {email_data.get('body', '')}"
                    
                    # Run AI processing in parallel
                    tasks = [
                        self.llm_service.process_prompt(categorization_prompt.template, email_content),
                        self.llm_service.process_prompt(action_prompt.template, email_content),
                        self.llm_service.process_prompt(summary_prompt.template, email_content)
                    ]
                    
                    category, action_items_raw, summary = await asyncio.gather(*tasks)
                    
                    # Parse action items
                    try:
                        if action_items_raw.strip().startswith('{') or action_items_raw.strip().startswith('['):
                            action_items = json.loads(action_items_raw)
                        else:
                            action_items = [{"task": action_items_raw, "deadline": None}]
                    except:
                        action_items = [{"task": action_items_raw, "deadline": None}]
                        
                except Exception as e:
                    print(f"⚠️ [EmailService] AI processing failed, using provided data: {e}")
            
            # Create email record
            email = Email(
                user_id=user_id,
                sender=email_data.get('sender', ''),
                subject=email_data.get('subject', ''),
                body=email_data.get('body', ''),
                timestamp=timestamp,
                category=category,
                priority=email_data.get('priority', 'medium'),
                is_read=email_data.get('is_read', False),
                is_archived=email_data.get('is_archived', False),
                is_starred=email_data.get('is_starred', False),
                action_items=action_items,
                summary=summary,
                email_metadata=email_data.get('metadata', {})
            )
            
            self.db.add(email)
            await self.db.commit()
            await self.db.refresh(email)
            
            print(f"✅ [EmailService] Email saved with ID: {email.id}")
            return email.to_dict()
            
        except Exception as e:
            print(f"❌ [EmailService] Error processing single email: {e}")
            import traceback
            print(f"❌ [EmailService] Stack trace: {traceback.format_exc()}")
            # Return the original data as fallback
            return email_data
    
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
            
            email_list = []
            for email in emails:
                try:
                    email_dict = email.to_dict()
                    email_list.append(email_dict)
                except Exception as e:
                    print(f"⚠️ [EmailService] Error converting email {email.id}: {e}")
                    email_list.append({
                        "id": str(email.id),
                        "user_id": str(email.user_id),
                        "sender": email.sender,
                        "subject": email.subject,
                        "body": email.body,
                        "timestamp": email.timestamp.isoformat(),
                        "category": email.category
                    })
            
            return email_list
            
        except Exception as e:
            print(f"❌ [EmailService] Error in get_user_emails: {e}")
            import traceback
            print(f"❌ [EmailService] Stack trace: {traceback.format_exc()}")
            return []
    
    async def get_email_by_id(self, email_id: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Get a specific email by ID, optionally filtered by user"""
        try:
            query = select(Email).where(Email.id == email_id)
            if user_id:
                query = query.where(Email.user_id == user_id)
                
            result = await self.db.execute(query)
            email = result.scalar_one_or_none()
            
            if email:
                print(f"✅ [EmailService] Found email: {email.id} - {email.subject}")
                return email.to_dict()
            else:
                print(f"❌ [EmailService] Email not found: {email_id} for user: {user_id}")
                return None
                
        except Exception as e:
            print(f"❌ [EmailService] Error getting email by ID: {e}")
            return None
    
    async def generate_reply_draft(self, email_id: str, user_id: str = None) -> str:
        """Generate a reply draft for an email"""
        try:
            print(f"📧 [EmailService] Generating reply for email: {email_id}")
            
            # Get the email
            email = await self.get_email_by_id(email_id, user_id)
            if not email:
                raise ValueError(f"Email not found: {email_id}")
            
            # Generate reply using LLM
            if self.llm_service:
                reply_data = await self.llm_service.generate_email_reply({
                    "sender": email.get('sender'),
                    "subject": email.get('subject'),
                    "body": email.get('body')
                })
                
                reply_body = reply_data.get('body', '')
                print(f"✅ [EmailService] Generated reply: {len(reply_body)} characters")
                return reply_body
            else:
                # Fallback reply
                sender_name = email.get('sender', 'there').split('@')[0]
                return f"""Dear {sender_name},

Thank you for your email regarding "{email.get('subject', 'this matter')}".

I have received your message and will review it carefully. Please expect a response within 24-48 hours.

Best regards,
User

---
[AI-generated draft]"""
                
        except Exception as e:
            print(f"❌ [EmailService] Error generating reply draft: {e}")
            return f"Error generating reply: {str(e)}"
    
    async def update_email_category(self, email_id: str, category: str, user_id: str = None) -> bool:
        """Update email category"""
        try:
            query = select(Email).where(Email.id == email_id)
            if user_id:
                query = query.where(Email.user_id == user_id)
                
            result = await self.db.execute(query)
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
            draft_metadata = draft_data.pop('metadata', {})
            draft_data['draft_metadata'] = draft_metadata
            
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
    
    async def ensure_user_has_emails(self, user_id: str) -> bool:
        """Ensure a user has emails (load mock data if empty)"""
        try:
            existing_emails = await self.get_user_emails(user_id)
            if not existing_emails:
                print(f"📧 [EmailService] No emails found for user {user_id}, loading mock data")
                await self.load_mock_emails(user_id)
                return True
            else:
                print(f"📧 [EmailService] User {user_id} already has {len(existing_emails)} emails")
                return True
        except Exception as e:
            print(f"❌ [EmailService] Error ensuring user has emails: {e}")
            return False
