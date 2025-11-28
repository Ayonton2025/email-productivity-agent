import json
import asyncio
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from app.core.config import settings

class LLMService:
    def __init__(self):
        self.provider = getattr(settings, 'LLM_PROVIDER', 'openai')
        
        # FIXED: Safe attribute access with fallbacks
        self.model = getattr(settings, 'LLM_MODEL', 'gpt-3.5-turbo')
        self.openai_client = None
        self.anthropic_client = None
        
        print(f"🔧 [LLMService] Initializing with provider: {self.provider}, model: {self.model}")
        
        try:
            openai_api_key = getattr(settings, 'OPENAI_API_KEY', None)
            anthropic_api_key = getattr(settings, 'ANTHROPIC_API_KEY', None)
            
            if self.provider == "openai" and openai_api_key:
                # FIXED: Simple initialization without proxies issue
                self.openai_client = AsyncOpenAI(api_key=openai_api_key)
                print(f"✅ [LLMService] OpenAI client initialized successfully")
            elif self.provider == "anthropic" and anthropic_api_key:
                self.anthropic_client = AsyncAnthropic(api_key=anthropic_api_key)
                print(f"✅ [LLMService] Anthropic client initialized successfully")
            else:
                print(f"⚠️ [LLMService] No valid LLM provider configured - using mock mode")
                print(f"🔍 [LLMService] Provider: {self.provider}, OpenAI Key: {bool(openai_api_key)}, Anthropic Key: {bool(anthropic_api_key)}")
        except Exception as e:
            print(f"❌ [LLMService] Failed to initialize LLM client: {e}")
            import traceback
            print(f"❌ [LLMService] Stack trace: {traceback.format_exc()}")
    
    async def process_prompt(self, prompt: str, email_content: str, system_message: str = None) -> str:
        """Process a prompt with email content using the configured LLM"""
        print(f"🤖 [LLMService] Processing prompt: {prompt[:100]}...")
        
        try:
            if self.provider == "openai" and self.openai_client:
                return await self._process_with_openai(prompt, email_content, system_message)
            elif self.provider == "anthropic" and self.anthropic_client:
                return await self._process_with_anthropic(prompt, email_content, system_message)
            else:
                return await self._mock_processing(prompt, email_content)
        except Exception as e:
            print(f"❌ [LLMService] Error in process_prompt: {e}")
            return f"Error processing request: {str(e)}"
    
    async def _process_with_openai(self, prompt: str, email_content: str, system_message: str) -> str:
        """Process using OpenAI GPT"""
        try:
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            
            user_content = f"Email Content:\n{email_content}\n\nInstruction: {prompt}"
            messages.append({"role": "user", "content": user_content})
            
            print(f"🚀 [LLMService] Calling OpenAI with model: {self.model}")
            
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1000,
                temperature=0.3
            )
            
            result = response.choices[0].message.content
            print(f"✅ [LLMService] OpenAI response received: {len(result)} characters")
            return result
            
        except Exception as e:
            print(f"❌ [LLMService] OpenAI API error: {e}")
            return f"OpenAI API error: {str(e)}"
    
    async def _process_with_anthropic(self, prompt: str, email_content: str, system_message: str) -> str:
        """Process using Anthropic Claude"""
        try:
            system_msg = system_message or "You are a helpful AI assistant."
            user_content = f"Email Content:\n{email_content}\n\nInstruction: {prompt}"
            
            print(f"🚀 [LLMService] Calling Anthropic Claude")
            
            response = await self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                temperature=0.3,
                system=system_msg,
                messages=[{"role": "user", "content": user_content}]
            )
            
            result = response.content[0].text
            print(f"✅ [LLMService] Anthropic response received: {len(result)} characters")
            return result
            
        except Exception as e:
            print(f"❌ [LLMService] Anthropic API error: {e}")
            return f"Anthropic API error: {str(e)}"
    
    async def _mock_processing(self, prompt: str, email_content: str) -> str:
        """Mock processing for testing without API keys"""
        print("🔄 [LLMService] Using mock processing")
        await asyncio.sleep(0.5)  # Simulate processing time
        
        # Enhanced mock responses
        if "categoriz" in prompt.lower():
            categories = ["Important", "Newsletter", "Spam", "To-Do"]
            category = categories[len(email_content) % 4]
            return json.dumps({"category": category, "confidence": 0.85})
            
        elif "action" in prompt.lower() or "task" in prompt.lower():
            return json.dumps({
                "tasks": [
                    {
                        "task": "Review the document mentioned in email", 
                        "deadline": "2024-01-15", 
                        "priority": "medium"
                    }
                ]
            })
            
        elif "reply" in prompt.lower() or "draft" in prompt.lower():
            sender_name = "there"
            if "From:" in email_content:
                # Extract sender name from email content
                for line in email_content.split('\n'):
                    if 'From:' in line:
                        sender_part = line.split('From:')[-1].strip()
                        if '@' in sender_part:
                            sender_name = sender_part.split('@')[0]
                        break
            
            return f"""Dear {sender_name},

Thank you for your email. I have received your message and will review it carefully.

I appreciate you taking the time to reach out and will get back to you with a proper response soon.

Best regards,
[Your Name]

---
[AI-generated draft - Mock response]"""
            
        elif "summar" in prompt.lower():
            summary_length = min(150, len(email_content))
            return f"This email appears to be about: {email_content[:summary_length]}... The main points discussed require your attention and follow-up."
            
        else:
            return f"I've processed your request regarding: {prompt[:80]}. Based on the email content, here's my analysis: This appears to be a message that requires your review and potential action."
    
    async def chat_with_agent(self, messages: List[Dict[str, str]], email_context: str = None) -> str:
        """Chat interface for the email agent"""
        print(f"💬 [LLMService] Chat with agent, messages: {len(messages)}")
        
        system_message = "You are an intelligent email productivity assistant. Help users manage their inbox, summarize emails, extract tasks, and draft responses."
        
        if email_context:
            system_message += f"\n\nCurrent email context:\n{email_context}"
        
        if self.provider == "openai" and self.openai_client:
            try:
                chat_messages = [{"role": "system", "content": system_message}]
                chat_messages.extend(messages)
                
                response = await self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=chat_messages,
                    max_tokens=500,
                    temperature=0.7
                )
                
                return response.choices[0].message.content
            except Exception as e:
                print(f"❌ [LLMService] Chat OpenAI error: {e}")
                return f"I encountered an error while processing your chat request: {str(e)}"
        else:
            # Enhanced mock response
            user_message = messages[-1]["content"] if messages else ""
            return f"I understand you're asking about: '{user_message[:100]}...'. As your email assistant, I can help you with:\n\n• Email categorization\n• Action item extraction\n• Reply drafting\n• Email summarization\n\nHow can I assist you with your email management today?"

    async def generate_email_reply(self, original_email: Dict[str, Any], tone: str = "professional") -> Dict[str, Any]:
        """Generate email reply using AI"""
        print(f"📧 [LLMService] Generating email reply with tone: {tone}")
        
        try:
            prompt = f"""
            Generate a {tone} email reply to this email:
            
            From: {original_email.get('sender', 'Unknown')}
            Subject: {original_email.get('subject', 'No Subject')}
            Body: {original_email.get('body', '')}
            
            Please create a thoughtful, {tone} response that addresses the key points.
            Return your response in JSON format with 'subject' and 'body' fields.
            Make sure the subject line is appropriate for a reply.
            """
            
            if self.provider == "openai" and self.openai_client:
                print("🚀 [LLMService] Using OpenAI for reply generation")
                
                try:
                    response = await self.openai_client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are a professional email assistant. Generate appropriate email replies in JSON format with 'subject' and 'body' fields."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        max_tokens=500,
                        response_format={"type": "json_object"}
                    )
                    
                    reply_data = json.loads(response.choices[0].message.content)
                    print(f"✅ [LLMService] Reply generated successfully")
                    
                    return {
                        "subject": reply_data.get("subject", f"Re: {original_email.get('subject', '')}"),
                        "body": reply_data.get("body", ""),
                        "tone": tone,
                        "ai_generated": True
                    }
                    
                except Exception as e:
                    print(f"❌ [LLMService] OpenAI reply generation error: {e}")
                    # Fall through to mock response
                    
            # Fallback to mock response (for both OpenAI errors and no provider)
            print("⚠️ [LLMService] Using mock reply generation")
            sender_name = original_email.get('sender', 'there').split('@')[0]
            
            return {
                "subject": f"Re: {original_email.get('subject', 'Your email')}",
                "body": f"""Dear {sender_name},

Thank you for your email regarding "{original_email.get('subject', 'this matter')}".

I've received your message and will review it carefully. I appreciate you reaching out and will get back to you with a proper response soon.

If this matter requires immediate attention, please don't hesitate to contact me directly.

Best regards,
[Your Name]

---
[AI-generated draft - System initializing]""",
                "tone": tone,
                "ai_generated": True
            }
                
        except Exception as e:
            print(f"❌ [LLMService] Error generating email reply: {e}")
            import traceback
            print(f"❌ [LLMService] Stack trace: {traceback.format_exc()}")
            
            # Safe fallback response
            return {
                "subject": f"Re: {original_email.get('subject', '')}",
                "body": f"""Thank you for your email. I've received your message regarding "{original_email.get('subject', 'this matter')}" and will review it shortly.

I appreciate you reaching out and will respond properly once I've had a chance to consider your message.

Best regards,
[Your Name]""",
                "tone": tone,
                "ai_generated": True,
                "error": str(e)
            }

    async def health_check(self) -> Dict[str, Any]:
        """Check LLM service health"""
        status = "healthy"
        details = []
        
        if self.provider == "openai" and self.openai_client:
            try:
                # Simple test call to check API connectivity
                test_response = await self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": "Say 'OK'"}],
                    max_tokens=5
                )
                details.append("OpenAI API: Connected")
            except Exception as e:
                status = "unhealthy"
                details.append(f"OpenAI API: Error - {str(e)}")
        elif self.provider == "anthropic" and self.anthropic_client:
            details.append("Anthropic API: Configured")
        else:
            status = "degraded"
            details.append("Using mock mode - No LLM provider configured")
        
        return {
            "status": status,
            "provider": self.provider,
            "model": self.model,
            "details": details
        }
