import openai
import os
from typing import List, Dict, Any, Optional
import json
import asyncio
from datetime import datetime

class EnhancedLLMService:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4')
        
    async def advanced_email_analysis(self, email_data: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
        """Perform advanced email analysis using OpenAI"""
        
        system_prompts = {
            "comprehensive_analysis": """
            You are an expert email analyst. Analyze the email comprehensively and provide:
            1. **Category**: Primary category (Important, Newsletter, Spam, To-Do, Personal, Work, Finance, Travel)
            2. **Priority**: Urgency level (critical, high, medium, low)
            3. **Sentiment**: Emotional tone (positive, negative, neutral, mixed)
            4. **Key Topics**: Main subjects discussed
            5. **Action Items**: Specific tasks with deadlines and priorities
            6. **Relationships**: Sender importance and relationship context
            7. **Follow-up**: Recommended follow-up actions
            8. **Summary**: Concise 2-3 sentence summary
            
            Respond with structured JSON.
            """,
            
            "cross_email_insights": """
            Analyze multiple emails together to identify patterns, trends, and insights across conversations.
            Provide relationship mapping, topic clustering, and timeline analysis.
            """,
            
            "smart_reply_generation": """
            Generate context-aware email replies that match the user's communication style.
            Consider relationship context, email history, and appropriate tone.
            """
        }
        
        prompt = system_prompts.get(analysis_type, system_prompts["comprehensive_analysis"])
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": self._format_email_for_analysis(email_data)}
                    ],
                    temperature=0.3,
                    max_tokens=1500,
                    response_format={"type": "json_object"}
                )
            )
            
            result = json.loads(response.choices[0].message.content)
            return self._enhance_analysis_result(result, email_data)
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return self._get_fallback_analysis(email_data)
    
    async def batch_process_emails(self, emails: List[Dict[str, Any]], analysis_type: str) -> List[Dict[str, Any]]:
        """Process multiple emails efficiently"""
        tasks = [self.advanced_email_analysis(email, analysis_type) for email in emails]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_emails = []
        for email, result in zip(emails, results):
            if isinstance(result, Exception):
                # Fallback processing
                processed_emails.append(self._get_fallback_analysis(email))
            else:
                email.update(result)
                processed_emails.append(email)
        
        return processed_emails
    
    async def conversational_agent(self, messages: List[Dict[str, str]], email_context: List[Dict] = None) -> str:
        """Advanced conversational agent with email context"""
        
        system_message = {
            "role": "system",
            "content": f"""
            You are InboxAI, an intelligent email productivity assistant. You have access to the user's email context and can provide sophisticated insights.
            
            Available Context:
            {self._format_email_context(email_context) if email_context else "No specific email context provided."}
            
            Capabilities:
            - Analyze email patterns and trends
            - Provide relationship insights
            - Suggest productivity optimizations
            - Draft context-aware responses
            - Identify urgent matters and deadlines
            
            Be helpful, concise, and focus on actionable insights.
            """
        }
        
        conversation_messages = [system_message] + messages
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=conversation_messages,
                    temperature=0.7,
                    max_tokens=1000
                )
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"I apologize, but I'm having trouble processing your request right now. Error: {str(e)}"
    
    async def generate_smart_reply(self, original_email: Dict[str, Any], tone: str = "professional", context: List[Dict] = None) -> Dict[str, Any]:
        """Generate intelligent email replies with context awareness"""
        
        tone_descriptions = {
            "professional": "formal, respectful, business-appropriate",
            "casual": "friendly, informal, conversational", 
            "formal": "very formal, structured, traditional business language",
            "friendly": "warm, personal, relationship-focused"
        }
        
        prompt = f"""
        Generate an email reply with the following tone: {tone_descriptions.get(tone, 'professional')}
        
        Original Email:
        From: {original_email.get('sender', 'Unknown')}
        Subject: {original_email.get('subject', 'No Subject')}
        Body: {original_email.get('body', '')}
        
        Additional Context: {self._format_email_context(context) if context else 'No additional context'}
        
        Please provide a well-structured reply that:
        1. Appropriately addresses all points from the original email
        2. Matches the specified tone
        3. Includes proper email formatting
        4. Considers any relationship context
        5. Suggests clear next steps if applicable
        
        Respond with JSON containing 'subject' and 'body' fields.
        """
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert email communication assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=800,
                    response_format={"type": "json_object"}
                )
            )
            
            reply_data = json.loads(response.choices[0].message.content)
            return {
                "subject": reply_data.get("subject", f"Re: {original_email.get('subject', '')}"),
                "body": reply_data.get("body", ""),
                "tone": tone,
                "ai_generated": True,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"Error generating smart reply: {e}")
            return self._get_fallback_reply(original_email, tone)
    
    def _format_email_for_analysis(self, email_data: Dict[str, Any]) -> str:
        """Format email data for AI analysis"""
        return f"""
        Email Analysis Request:
        
        Sender: {email_data.get('sender', 'Unknown')}
        Subject: {email_data.get('subject', 'No Subject')}
        Date: {email_data.get('timestamp', 'Unknown')}
        Body: {email_data.get('body', '')}
        
        Additional Metadata:
        - Provider: {email_data.get('provider', 'unknown')}
        - Priority: {email_data.get('priority', 'unknown')}
        - Category: {email_data.get('category', 'uncategorized')}
        """
    
    def _format_email_context(self, emails: List[Dict[str, Any]]) -> str:
        """Format multiple emails for context"""
        if not emails:
            return "No email context available."
        
        context_str = "Email Context:\n\n"
        for i, email in enumerate(emails[:5]):  # Limit context to 5 recent emails
            context_str += f"Email {i+1}:\n"
            context_str += f"From: {email.get('sender', 'Unknown')}\n"
            context_str += f"Subject: {email.get('subject', 'No Subject')}\n"
            context_str += f"Date: {email.get('timestamp', 'Unknown')}\n"
            context_str += f"Summary: {email.get('summary', 'No summary')}\n\n"
        
        return context_str
    
    def _enhance_analysis_result(self, result: Dict[str, Any], original_email: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance AI analysis with additional metadata"""
        result["analysis_timestamp"] = datetime.utcnow().isoformat()
        result["model_used"] = self.model
        result["original_email_id"] = original_email.get("id")
        
        # Add confidence scores if not present
        if "confidence_scores" not in result:
            result["confidence_scores"] = {
                "categorization": 0.85,
                "priority": 0.80,
                "sentiment": 0.75
            }
        
        return result
    
    def _get_fallback_analysis(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide fallback analysis when AI fails"""
        return {
            "category": "Uncategorized",
            "priority": "medium",
            "sentiment": "neutral",
            "key_topics": ["general"],
            "action_items": [],
            "summary": "Basic analysis completed.",
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "is_fallback": True
        }
    
    def _get_fallback_reply(self, original_email: Dict[str, Any], tone: str) -> Dict[str, Any]:
        """Provide fallback reply when AI fails"""
        return {
            "subject": f"Re: {original_email.get('subject', '')}",
            "body": "Thank you for your email. I will review this and get back to you shortly.",
            "tone": tone,
            "ai_generated": True,
            "is_fallback": True,
            "generated_at": datetime.utcnow().isoformat()
        }