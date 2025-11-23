import json
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import WebSocket

from app.services.llm_service import LLMService
from app.services.email_service import EmailService

class AgentService:
    def __init__(self, db: AsyncSession, websocket: WebSocket):
        self.db = db
        self.websocket = websocket
        self.llm_service = LLMService()
        self.email_service = EmailService(db)
        self.conversation_history = []
    
    async def handle_message(self, data: Dict[str, Any]):
        """Handle incoming WebSocket messages"""
        message_type = data.get('type')
        
        if message_type == 'chat':
            await self.handle_chat_message(data)
        elif message_type == 'process_email':
            await self.handle_email_processing(data)
        elif message_type == 'generate_draft':
            await self.handle_draft_generation(data)
    
    async def handle_chat_message(self, data: Dict[str, Any]):
        """Handle chat messages with the email agent"""
        user_message = data.get('message', '')
        email_context = data.get('email_context')
        
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # Get response from LLM
        response = await self.llm_service.chat_with_agent(self.conversation_history, email_context)
        
        # Add assistant response to history
        self.conversation_history.append({"role": "assistant", "content": response})
        
        # Send response back
        await self.websocket.send_json({
            "type": "chat_response",
            "message": response,
            "conversation_id": data.get('conversation_id')
        })
    
    async def handle_email_processing(self, data: Dict[str, Any]):
        """Handle email processing requests"""
        email_id = data.get('email_id')
        action = data.get('action')  # summarize, extract_tasks, categorize, etc.
        
        email = await self.email_service.get_email_by_id(email_id)
        if not email:
            await self.websocket.send_json({
                "type": "error",
                "message": "Email not found"
            })
            return
        
        email_content = f"From: {email['sender']}\nSubject: {email['subject']}\nBody: {email['body']}"
        
        if action == "summarize":
            prompt = "Provide a concise summary of this email, highlighting key points and required actions."
        elif action == "extract_tasks":
            prompt = "Extract all actionable tasks from this email with their deadlines and priorities."
        elif action == "categorize":
            prompt = "Categorize this email and explain your reasoning."
        else:
            prompt = data.get('custom_prompt', "Analyze this email and provide insights.")
        
        result = await self.llm_service.process_prompt(prompt, email_content)
        
        await self.websocket.send_json({
            "type": "processing_result",
            "action": action,
            "email_id": email_id,
            "result": result
        })
    
    async def handle_draft_generation(self, data: Dict[str, Any]):
        """Handle email draft generation"""
        context_email_id = data.get('context_email_id')
        tone = data.get('tone', 'professional')
        custom_instructions = data.get('instructions', '')
        
        context_email = None
        if context_email_id:
            context_email = await self.email_service.get_email_by_id(context_email_id)
        
        if context_email:
            email_context = f"Replying to email from {context_email['sender']} with subject: {context_email['subject']}\n\nOriginal email content:\n{context_email['body']}"
            prompt = f"Draft a {tone} email reply. {custom_instructions}"
        else:
            email_context = "Composing a new email"
            prompt = f"Draft a {tone} email. {custom_instructions}"
        
        draft_content = await self.llm_service.process_prompt(prompt, email_context)
        
        # Create draft record
        draft_data = {
            "subject": f"Re: {context_email['subject']}" if context_email else "New Email Draft",
            "body": draft_content,
            "recipient": context_email['sender'] if context_email else "",
            "context_email_id": context_email_id,
            "metadata": {
                "tone": tone,
                "ai_generated": True,
                "custom_instructions": custom_instructions
            }
        }
        
        draft = await self.email_service.create_draft(draft_data)
        
        await self.websocket.send_json({
            "type": "draft_generated",
            "draft": draft,
            "context_email_id": context_email_id
        })