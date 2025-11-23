import json
import asyncio
from typing import Dict, Any, List, Optional
import openai
from anthropic import Anthropic
from app.core.config import settings

class LLMService:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.openai_client = None
        self.anthropic_client = None
        
        if self.provider == "openai" and settings.OPENAI_API_KEY:
            self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        elif self.provider == "anthropic" and settings.ANTHROPIC_API_KEY:
            self.anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    async def process_prompt(self, prompt: str, email_content: str, system_message: str = None) -> str:
        """Process a prompt with email content using the configured LLM"""
        
        if self.provider == "openai" and self.openai_client:
            return await self._process_with_openai(prompt, email_content, system_message)
        elif self.provider == "anthropic" and self.anthropic_client:
            return await self._process_with_anthropic(prompt, email_content, system_message)
        else:
            return await self._mock_processing(prompt, email_content)
    
    async def _process_with_openai(self, prompt: str, email_content: str, system_message: str) -> str:
        """Process using OpenAI GPT"""
        try:
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            
            messages.extend([
                {"role": "user", "content": f"Email Content:\n{email_content}\n\nInstruction: {prompt}"}
            ])
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=1000,
                temperature=0.3
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return f"Error processing with OpenAI: {str(e)}"
    
    async def _process_with_anthropic(self, prompt: str, email_content: str, system_message: str) -> str:
        """Process using Anthropic Claude"""
        try:
            full_prompt = f"{system_message}\n\nEmail Content:\n{email_content}\n\nInstruction: {prompt}"
            
            response = self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                temperature=0.3,
                messages=[{"role": "user", "content": full_prompt}]
            )
            
            return response.content[0].text
        except Exception as e:
            print(f"Anthropic API error: {e}")
            return f"Error processing with Anthropic: {str(e)}"
    
    async def _mock_processing(self, prompt: str, email_content: str) -> str:
        """Mock processing for testing without API keys"""
        await asyncio.sleep(1)  # Simulate processing time
        
        if "categoriz" in prompt.lower():
            categories = ["Important", "Newsletter", "Spam", "To-Do"]
            return categories[len(email_content) % 4]
        elif "action" in prompt.lower() or "task" in prompt.lower():
            return json.dumps({
                "task": "Review the document mentioned in email",
                "deadline": "2024-01-15",
                "priority": "medium"
            })
        elif "reply" in prompt.lower() or "draft" in prompt.lower():
            return "Thank you for your email. I will review this and get back to you shortly."
        elif "summar" in prompt.lower():
            return f"Summary: This email discusses {email_content[:50]}..."
        else:
            return f"Processed: {prompt[:50]}..."
    
    async def chat_with_agent(self, messages: List[Dict[str, str]], email_context: str = None) -> str:
        """Chat interface for the email agent"""
        system_message = "You are an intelligent email productivity assistant. Help users manage their inbox, summarize emails, extract tasks, and draft responses."
        
        if email_context:
            system_message += f"\n\nCurrent email context:\n{email_context}"
        
        if self.provider == "openai" and self.openai_client:
            chat_messages = [{"role": "system", "content": system_message}]
            chat_messages.extend(messages)
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=chat_messages,
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        else:
            # Mock response
            user_message = messages[-1]["content"] if messages else ""
            return f"I understand you're asking about: {user_message[:100]}. As your email assistant, I can help you categorize, summarize, and manage your emails effectively."