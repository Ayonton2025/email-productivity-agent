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
            if existing_emails and len(existing_emails) > 0:
                print(f"📧 [EmailService] User already has {len(existing_emails)} emails, skipping mock load")
                return existing_emails
            
            # Try multiple possible paths for the mock data file
            possible_paths = [
                "data/mock_inbox.json",
                "./data/mock_inbox.json", 
                "backend/data/mock_inbox.json",
                "./backend/data/mock_inbox.json",
                "../data/mock_inbox.json",
                "./../data/mock_inbox.json"
            ]
            
            mock_emails = []
            file_found = False
            
            for file_path in possible_paths:
                if os.path.exists(file_path):
                    print(f"✅ [EmailService] Found mock data file: {file_path}")
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            mock_emails = json.load(f)
                        file_found = True
                        break
                    except Exception as e:
                        print(f"❌ [EmailService] Error reading {file_path}: {e}")
                        continue
            
            if not file_found:
                print(f"❌ [EmailService] Mock data file not found in any location. Tried: {possible_paths}")
                # Use hardcoded mock data as fallback - WITH ALL 20 EMAILS
                mock_emails = self._get_hardcoded_mock_emails()
            
            print(f"📧 [EmailService] Found {len(mock_emails)} mock emails to load")
            
            processed_emails = []
            for email_data in mock_emails:
                # Ensure each email has required fields for processing
                if 'category' not in email_data:
                    email_data['category'] = 'Uncategorized'
                if 'priority' not in email_data:
                    email_data['priority'] = 'medium'
                if 'is_read' not in email_data:
                    email_data['is_read'] = False
                if 'is_archived' not in email_data:
                    email_data['is_archived'] = False
                if 'is_starred' not in email_data:
                    email_data['is_starred'] = False
                if 'action_items' not in email_data:
                    email_data['action_items'] = []
                if 'summary' not in email_data:
                    email_data['summary'] = ''
                
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
        """Fallback hardcoded mock emails if JSON file is missing - ALL 20 EMAILS"""
        return [
            {
                "id": "1",
                "sender": "project.manager@company.com",
                "subject": "Q4 Project Review Meeting",
                "body": "Hi team,\n\nWe need to schedule the Q4 project review meeting for next week. Please review the attached project report and come prepared to discuss:\n\n1. Project milestones achieved\n2. Budget utilization\n3. Resource allocation for Q1\n4. Risk assessment\n\nLet me know your availability for Tuesday or Wednesday.\n\nBest regards,\nSarah Chen\nProject Manager",
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
                "sender": "newsletter@techdaily.com",
                "subject": "Tech Daily: AI Trends in 2024",
                "body": "Welcome to this week's Tech Daily newsletter!\n\nFeatured Articles:\n- The Rise of Multimodal AI Systems\n- Quantum Computing Breakthroughs\n- Sustainable Tech Innovations\n- Developer Tools of the Year\n\nRead more: https://techdaily.com/ai-trends-2024\n\nUnsubscribe: https://techdaily.com/unsubscribe",
                "timestamp": "2024-01-08T08:15:00Z",
                "category": "Newsletter",
                "priority": "low",
                "is_read": True,
                "is_archived": False,
                "is_starred": False,
                "action_items": [],
                "summary": "Weekly tech newsletter featuring AI trends and developments",
                "metadata": {"type": "newsletter", "frequency": "weekly"}
            },
            {
                "id": "3",
                "sender": "hr@company.com", 
                "subject": "ACTION REQUIRED: Benefits Enrollment Deadline",
                "body": "Dear Employee,\n\nThis is a reminder that the benefits enrollment period closes this Friday, January 12th, 2024 at 5:00 PM.\n\nYou must:\n1. Review your benefit selections\n2. Update dependent information if needed\n3. Submit your enrollment form\n\nPlease complete this by the deadline to avoid interruption in your benefits coverage.\n\nHR Department",
                "timestamp": "2024-01-08T09:45:00Z",
                "category": "To-Do",
                "priority": "high",
                "is_read": False,
                "is_archived": False,
                "is_starred": False,
                "action_items": [
                    {"task": "Complete benefits enrollment", "deadline": "2024-01-12", "priority": "high"}
                ],
                "summary": "Benefits enrollment reminder with Friday deadline",
                "metadata": {"type": "task_request", "action_required": True}
            },
            {
                "id": "4",
                "sender": "noreply@security-alert.com",
                "subject": "URGENT: Your Account Has Been Compromised",
                "body": "SECURITY ALERT: We detected suspicious activity on your account.\n\nClick here immediately to verify your identity and secure your account:\nhttp://fake-security-site.com/verify\n\nIf you don't act within 24 hours, your account will be suspended.\n\nThis is an automated message. Do not reply.",
                "timestamp": "2024-01-08T07:20:00Z",
                "category": "Spam",
                "priority": "low",
                "is_read": False,
                "is_archived": False,
                "is_starred": False,
                "action_items": [],
                "summary": "Suspicious security alert email - likely phishing attempt",
                "metadata": {"type": "spam", "suspicious": True}
            },
            {
                "id": "5",
                "sender": "colleague@company.com",
                "subject": "Lunch Meeting Tomorrow?",
                "body": "Hey!\n\nAre you free for lunch tomorrow around 12:30? I wanted to discuss the new marketing campaign and get your thoughts on the creative direction.\n\nThere's that new Italian place that just opened near the office - want to try it?\n\nLet me know!\n\nCheers,\nMike",
                "timestamp": "2024-01-08T11:10:00Z",
                "category": "Personal",
                "priority": "low",
                "is_read": True,
                "is_archived": False,
                "is_starred": False,
                "action_items": [
                    {"task": "Respond to lunch invitation", "deadline": "2024-01-09", "priority": "low"}
                ],
                "summary": "Informal lunch invitation from colleague",
                "metadata": {"type": "personal", "informal": True}
            },
            {
                "id": "6",
                "sender": "client.success@software.com",
                "subject": "Your Premium Trial Ends in 3 Days",
                "body": "Hi there,\n\nYour premium trial for SuperSoftware ends in 3 days. Here's what you'll lose access to:\n\n- Advanced analytics dashboard\n- Custom reporting features\n- Priority support\n- Team collaboration tools\n\nUpgrade now to maintain access: https://supersoftware.com/upgrade\n\nQuestions? Reply to this email!\n\nBest,\nThe SuperSoftware Team",
                "timestamp": "2024-01-08T06:30:00Z",
                "category": "Newsletter",
                "priority": "medium",
                "is_read": False,
                "is_archived": False,
                "is_starred": False,
                "action_items": [
                    {"task": "Evaluate software trial before expiration", "deadline": "2024-01-11", "priority": "medium"}
                ],
                "summary": "Software trial expiration notice with upgrade offer",
                "metadata": {"type": "commercial", "trial_expiring": True}
            },
            {
                "id": "7",
                "sender": "ceo@company.com",
                "subject": "Company All-Hands Meeting This Friday",
                "body": "Team,\n\nWe'll be holding our quarterly all-hands meeting this Friday at 2:00 PM in the main auditorium.\n\nAgenda:\n- 2023 Year in Review\n- 2024 Strategic Direction\n- New Product Announcements\n- Q&A Session\n\nAttendance is mandatory for all employees. Please arrive 10 minutes early.\n\nLooking forward to seeing everyone there!\n\nJohn Smith\nCEO",
                "timestamp": "2024-01-07T16:45:00Z",
                "category": "Important",
                "priority": "high",
                "is_read": False,
                "is_archived": False,
                "is_starred": False,
                "action_items": [
                    {"task": "Attend all-hands meeting", "deadline": "2024-01-12", "priority": "high"}
                ],
                "summary": "Mandatory company-wide all-hands meeting announcement",
                "metadata": {"type": "company_announcement", "mandatory": True}
            },
            {
                "id": "8",
                "sender": "dev-team@project.com",
                "subject": "Code Review Request: Feature/Auth-Integration",
                "body": "Hello team,\n\nI've completed work on the authentication integration feature and have opened a pull request.\n\nKey changes:\n- Implemented OAuth2 flow\n- Added multi-factor authentication\n- Updated user session management\n- Enhanced security middleware\n\nPlease review the PR: https://github.com/company/repo/pull/142\n\nI need this reviewed by EOD tomorrow for the sprint deadline.\n\nThanks,\nAlex Rodriguez\nSenior Developer",
                "timestamp": "2024-01-07T14:20:00Z",
                "category": "To-Do",
                "priority": "medium",
                "is_read": False,
                "is_archived": False,
                "is_starred": False,
                "action_items": [
                    {"task": "Review authentication feature code", "deadline": "2024-01-09", "priority": "medium"}
                ],
                "summary": "Code review request for authentication integration feature",
                "metadata": {"type": "technical", "deadline": "2024-01-09"}
            },
            {
                "id": "9",
                "sender": "invoice@supplier.com",
                "subject": "Invoice #INV-2024-001 - Payment Due",
                "body": "INVOICE\n\nInvoice Number: INV-2024-001\nDate: January 5, 2024\nDue Date: January 19, 2024\nAmount Due: $4,250.00\n\nServices Rendered:\n- Monthly software license: $3,500.00\n- Technical support: $750.00\n\nPayment Methods:\n- Bank Transfer (details attached)\n- Credit Card (link in portal)\n\nPlease process payment by the due date.\n\nThank you for your business!\n\nAccounting Department\nGlobal Supplier Inc.",
                "timestamp": "2024-01-07T11:15:00Z",
                "category": "To-Do",
                "priority": "medium",
                "is_read": False,
                "is_archived": False,
                "is_starred": False,
                "action_items": [
                    {"task": "Process invoice payment", "deadline": "2024-01-19", "priority": "medium"}
                ],
                "summary": "Invoice for software license and technical support services",
                "metadata": {"type": "financial", "amount": 4250.00}
            },
            {
                "id": "10",
                "sender": "conference@ai-summit.org",
                "subject": "You're Invited: Global AI Summit 2024",
                "body": "Dear AI Enthusiast,\n\nYou are invited to attend the Global AI Summit 2024 in San Francisco, March 15-17.\n\nFeatured Speakers:\n- Dr. Jane Smith, AI Research Director\n- Mark Johnson, CTO of Tech Innovations\n- Sarah Lee, Ethics in AI Expert\n\nEarly bird registration ends January 31st.\nRegister now: https://ai-summit.org/register-2024\n\nWe hope to see you there!\n\nConference Team\nGlobal AI Summit",
                "timestamp": "2024-01-07T09:30:00Z",
                "category": "Newsletter",
                "priority": "low",
                "is_read": True,
                "is_archived": False,
                "is_starred": False,
                "action_items": [
                    {"task": "Consider AI Summit registration", "deadline": "2024-01-31", "priority": "low"}
                ],
                "summary": "Invitation to Global AI Summit conference",
                "metadata": {"type": "event", "early_bird": True}
            },
            {
                "id": "11",
                "sender": "recruiting@techcorp.com",
                "subject": "Interview Invitation: Senior Developer Position",
                "body": "Dear Candidate,\n\nThank you for your application for the Senior Developer position at TechCorp.\n\nWe were impressed with your background and would like to invite you for a technical interview.\n\nDate: January 15, 2024\nTime: 2:00 PM EST\nFormat: Video Call (Zoom link will be sent)\nDuration: 60 minutes\n\nPlease confirm your availability by replying to this email.\n\nBest regards,\nRecruiting Team\nTechCorp",
                "timestamp": "2024-01-06T15:20:00Z",
                "category": "Important",
                "priority": "high",
                "is_read": False,
                "is_archived": False,
                "is_starred": False,
                "action_items": [
                    {"task": "Confirm interview availability", "deadline": "2024-01-08", "priority": "high"},
                    {"task": "Prepare for technical interview", "deadline": "2024-01-15", "priority": "medium"}
                ],
                "summary": "Interview invitation for Senior Developer position",
                "metadata": {"type": "recruiting", "interview_date": "2024-01-15"}
            },
            {
                "id": "12",
                "sender": "support@cloudservice.com",
                "subject": "Scheduled Maintenance Notice",
                "body": "Maintenance Notification\n\nWe will be performing scheduled maintenance on our cloud infrastructure:\n\nDate: January 10, 2024\nTime: 2:00 AM - 6:00 AM UTC\nImpact: Service may be intermittently unavailable\n\nThis maintenance includes:\n- Database optimization\n- Security patches\n- Performance improvements\n\nWe apologize for any inconvenience and appreciate your understanding.\n\nCloud Services Team",
                "timestamp": "2024-01-06T13:45:00Z",
                "category": "Newsletter",
                "priority": "low",
                "is_read": True,
                "is_archived": False,
                "is_starred": False,
                "action_items": [],
                "summary": "Scheduled maintenance notification for cloud infrastructure",
                "metadata": {"type": "maintenance", "duration": "4 hours"}
            },
            {
                "id": "13",
                "sender": "travel@airline.com",
                "subject": "Your Flight Itinerary: NYC to SFO",
                "body": "FLIGHT CONFIRMATION\n\nPassenger: John Doe\nBooking Reference: AB7X9K\n\nFlight: AA2456\nRoute: New York (JFK) to San Francisco (SFO)\nDate: January 20, 2024\nDeparture: 8:15 AM\nArrival: 11:45 AM\nSeat: 14A\n\nFlight: AA2891\nRoute: San Francisco (SFO) to New York (JFK)\nDate: January 25, 2024\nDeparture: 4:30 PM\nArrival: 12:45 AM (+1)\nSeat: 22C\n\nCheck-in opens 24 hours before departure.\nSafe travels!\n\nAirline Operations",
                "timestamp": "2024-01-06T11:30:00Z",
                "category": "Personal",
                "priority": "medium",
                "is_read": False,
                "is_archived": False,
                "is_starred": False,
                "action_items": [
                    {"task": "Check in for flights", "deadline": "2024-01-19", "priority": "medium"}
                ],
                "summary": "Flight itinerary confirmation for New York to San Francisco trip",
                "metadata": {"type": "travel", "round_trip": True}
            },
            {
                "id": "14",
                "sender": "marketing@ecommerce.com",
                "subject": "Your Order #789123 Has Shipped!",
                "body": "Great news! Your order has shipped.\n\nOrder #789123\nShipped: January 6, 2024\nEstimated Delivery: January 9, 2024\nTracking Number: 1Z987XYZ654321\n\nItems Shipped:\n- Wireless Headphones (Qty: 1)\n- USB-C Cable (Qty: 2)\n\nTrack your package: https://tracking.com/1Z987XYZ654321\n\nThank you for your purchase!\n\nCustomer Service Team",
                "timestamp": "2024-01-06T10:15:00Z",
                "category": "Personal",
                "priority": "low",
                "is_read": True,
                "is_archived": False,
                "is_starred": False,
                "action_items": [
                    {"task": "Track package delivery", "deadline": "2024-01-09", "priority": "low"}
                ],
                "summary": "Order shipment confirmation with tracking information",
                "metadata": {"type": "shipping", "estimated_delivery": "2024-01-09"}
            },
            {
                "id": "15",
                "sender": "legal@company.com",
                "subject": "Contract Review: Client Services Agreement",
                "body": "Dear Team,\n\nPlease review the attached Client Services Agreement for our new partnership with Global Solutions Inc.\n\nKey points requiring attention:\n- Section 4.2: Service Level Agreements\n- Section 7.3: Intellectual Property Rights\n- Section 9.1: Termination Clauses\n- Appendix B: Pricing Schedule\n\nPlease provide your feedback by EOD Friday.\n\nLegal Department",
                "timestamp": "2024-01-05T16:40:00Z",
                "category": "Important",
                "priority": "high",
                "is_read": False,
                "is_archived": False,
                "is_starred": False,
                "action_items": [
                    {"task": "Review client services agreement", "deadline": "2024-01-12", "priority": "high"}
                ],
                "summary": "Legal contract review request for new partnership agreement",
                "metadata": {"type": "legal", "attachments": 1, "deadline": "2024-01-12"}
            },
            {
                "id": "16",
                "sender": "training@devskills.org",
                "subject": "Advanced Python Workshop - Registration Confirmation",
                "body": "Registration Confirmed!\n\nWorkshop: Advanced Python for Data Engineering\nDate: January 18-19, 2024\nTime: 9:00 AM - 5:00 PM Daily\nLocation: Virtual (Zoom)\n\nWhat to bring:\n- Laptop with Python 3.8+ installed\n- Text editor/IDE of your choice\n- Curiosity and questions!\n\nCourse materials will be shared 24 hours before the workshop.\n\nWe look forward to seeing you there!\n\nDevSkills Training Team",
                "timestamp": "2024-01-05T14:25:00Z",
                "category": "Personal",
                "priority": "low",
                "is_read": True,
                "is_archived": False,
                "is_starred": False,
                "action_items": [
                    {"task": "Prepare for Python workshop", "deadline": "2024-01-17", "priority": "low"}
                ],
                "summary": "Registration confirmation for Advanced Python workshop",
                "metadata": {"type": "training", "workshop_date": "2024-01-18"}
            },
            {
                "id": "17",
                "sender": "system@monitoring.com",
                "subject": "ALERT: High CPU Usage Detected",
                "body": "SYSTEM ALERT\n\nServer: production-web-03\nCPU Usage: 95% (Threshold: 85%)\nMemory Usage: 78%\nDuration: 15 minutes\n\nRecommended Actions:\n1. Check application logs for errors\n2. Review recent deployments\n3. Monitor database connections\n4. Consider scaling resources\n\nNext alert in 30 minutes if issue persists.\n\nSystem Monitoring Bot",
                "timestamp": "2024-01-05T12:50:00Z",
                "category": "Important",
                "priority": "high",
                "is_read": False,
                "is_archived": False,
                "is_starred": False,
                "action_items": [
                    {"task": "Investigate high CPU usage", "deadline": "2024-01-05", "priority": "high"},
                    {"task": "Check application logs", "deadline": "2024-01-05", "priority": "medium"}
                ],
                "summary": "System alert for high CPU usage on production server",
                "metadata": {"type": "alert", "severity": "high"}
            },
            {
                "id": "18",
                "sender": "partner@collaboration.com",
                "subject": "Partnership Proposal: Joint Marketing Initiative",
                "body": "Dear Business Partner,\n\nWe're excited to propose a joint marketing initiative for Q1 2024.\n\nProposal Highlights:\n- Co-branded webinar series\n- Joint case study development\n- Cross-promotion in newsletters\n- Shared social media campaign\n\nExpected Outcomes:\n- 25% increase in lead generation\n- Expanded market reach\n- Enhanced brand visibility\n\nLet's schedule a call to discuss further.\n\nBest regards,\nPartnership Team",
                "timestamp": "2024-01-05T10:35:00Z",
                "category": "Important",
                "priority": "medium",
                "is_read": False,
                "is_archived": False,
                "is_starred": False,
                "action_items": [
                    {"task": "Review partnership proposal", "deadline": "2024-01-12", "priority": "medium"},
                    {"task": "Schedule call with partnership team", "deadline": "2024-01-15", "priority": "medium"}
                ],
                "summary": "Partnership proposal for joint marketing initiative",
                "metadata": {"type": "partnership", "q1_initiative": True}
            },
            {
                "id": "19",
                "sender": "finance@accounting.com",
                "subject": "Monthly Expense Report Submission Reminder",
                "body": "Expense Report Reminder\n\nThis is a friendly reminder that monthly expense reports for December 2023 are due by January 10th, 2024.\n\nRequired Documentation:\n- Receipts for all expenses over $25\n- Business purpose for each expense\n- Project/client code if applicable\n\nSubmit via: https://expense.portal.com\n\nLate submissions may delay reimbursement.\n\nFinance Department",
                "timestamp": "2024-01-05T09:20:00Z",
                "category": "To-Do",
                "priority": "medium",
                "is_read": False,
                "is_archived": False,
                "is_starred": False,
                "action_items": [
                    {"task": "Submit December expense report", "deadline": "2024-01-10", "priority": "medium"}
                ],
                "summary": "Reminder for monthly expense report submission deadline",
                "metadata": {"type": "finance", "deadline": "2024-01-10"}
            },
            {
                "id": "20",
                "sender": "social@linkedin.com",
                "subject": "You have 5 new connection requests",
                "body": "Hi John,\n\nYou have 5 new connection requests waiting:\n\n- Sarah Johnson (Tech Industry)\n- Mike Chen (Software Development)\n- Dr. Emily Wong (AI Research)\n- Robert Garcia (Product Management)\n- Lisa Thompson (Data Science)\n\nView and respond to your connection requests:\nhttps://linkedin.com/mynetwork\n\nStay connected,\nThe LinkedIn Team",
                "timestamp": "2024-01-05T07:45:00Z",
                "category": "Personal",
                "priority": "low",
                "is_read": True,
                "is_archived": False,
                "is_starred": False,
                "action_items": [
                    {"task": "Review LinkedIn connection requests", "deadline": "2024-01-12", "priority": "low"}
                ],
                "summary": "Notification of new LinkedIn connection requests",
                "metadata": {"type": "social", "platform": "linkedin"}
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
            if not existing_emails or len(existing_emails) == 0:
                print(f"📧 [EmailService] No emails found for user {user_id}, loading mock data")
                await self.load_mock_emails(user_id)
                return True
            else:
                print(f"📧 [EmailService] User {user_id} already has {len(existing_emails)} emails")
                return True
        except Exception as e:
            print(f"❌ [EmailService] Error ensuring user has emails: {e}")
            return False
