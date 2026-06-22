import asyncio
import json
import re
from email.utils import parseaddr
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.llm_orchestration_service import llm_service as orchestrator


class LLMService:
    def __init__(self):
        self.model = getattr(settings, "LLM_MODEL", "gpt-4o-mini")
        self.default_temperature = float(getattr(settings, "AI_TEMPERATURE", 0.3) or 0.3)
        self.max_tokens = int(getattr(settings, "MAX_TOKENS", 1000) or 1000)
        self.orchestrator = orchestrator

    async def process_prompt(self, prompt: str, email_content: str, system_message: str = None) -> str:
        """Process a prompt with email content using orchestrated provider chain."""
        try:
            full_prompt = f"Email Content:\n{email_content}\n\nInstruction: {prompt}"
            result = await self.orchestrator.call_llm(
                prompt=full_prompt,
                system_prompt=system_message,
                model=self.model,
                temperature=self.default_temperature,
                max_tokens=self.max_tokens,
                feature="process_prompt",
                session=None,
            )
            if result.get("success") and result.get("response"):
                return result["response"]
        except Exception:
            pass
        return await self._mock_processing(prompt, email_content, system_message)

    @staticmethod
    def _parse_json_object(raw: str) -> Dict[str, Any]:
        text = (raw or "").strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}

    async def _mock_processing(self, prompt: str, email_content: str, system_message: str = None) -> str:
        await asyncio.sleep(0.2)

        if "categoriz" in prompt.lower():
            categories = ["Important", "Newsletter", "Spam", "To-Do", "Work", "Personal"]
            category = categories[len(email_content) % len(categories)]
            return json.dumps({"category": category, "confidence": 0.85, "mock": True})

        if "action" in prompt.lower() or "task" in prompt.lower() or "extract" in prompt.lower():
            return json.dumps(
                {
                    "tasks": [
                        {"task": "Review the request", "deadline": None, "priority": "medium", "assigned_to": "You"},
                        {"task": "Reply to sender", "deadline": None, "priority": "low", "assigned_to": "You"},
                    ],
                    "mock": True,
                }
            )

        if "reply" in prompt.lower() or "draft" in prompt.lower():
            sender_name = "there"
            if "From:" in email_content:
                for line in email_content.split("\n"):
                    if "From:" in line:
                        sender_part = line.split("From:")[-1].strip()
                        if "@" in sender_part:
                            sender_name = sender_part.split("@")[0]
                        break
            return (
                f"Dear {sender_name},\n\n"
                "Thank you for your email. I have received your message and will review it carefully.\n\n"
                "Best regards,\nTeam\n\n[AI-generated draft - Mock response]"
            )

        if "summar" in prompt.lower():
            summary_length = min(150, len(email_content))
            return f"This email appears to be about: {email_content[:summary_length]}... [Mock summary]"

        return "I processed your request based on the email content. [Mock response]"

    async def chat_with_agent(self, messages: List[Dict[str, str]], email_context: str = None) -> str:
        """Chat interface for the email agent."""
        system_message = "You are an intelligent email productivity assistant."
        if email_context:
            system_message += f"\n\nCurrent email context:\n{email_context}"

        user_message = messages[-1]["content"] if messages else ""

        try:
            prompt = "\n".join([m.get("content", "") for m in messages])
            result = await self.orchestrator.call_llm(
                prompt=prompt,
                system_prompt=system_message,
                model=self.model,
                temperature=0.7,
                max_tokens=500,
                feature="chat",
                session=None,
            )
            if result.get("success") and result.get("response"):
                return result["response"]
        except Exception:
            pass

        return (
            f"I understand you're asking about: '{user_message[:100]}...'. "
            "I can help with categorization, extraction, summaries, and reply drafts. [Mock response]"
        )

    async def generate_email_reply(
        self,
        original_email: Dict[str, Any],
        tone: str = "professional",
        user_plan: str = "personal",
        user_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate an email reply using configured provider."""
        sender_email = original_email.get("sender", "Unknown")
        sender_name = self._extract_sender_name(sender_email)
        email_subject = original_email.get("subject", "Your email")
        email_body = original_email.get("body", "")

        prompt = f"""Generate a {tone} email reply as JSON.

Original Email:
From: {sender_email}
Subject: {email_subject}
Body: {email_body[:2000]}

        Return JSON with:
        - subject
        - body
        - confidence
        """

        try:
            result = await self.orchestrator.call_llm(
                prompt=prompt,
                system_prompt="You are a professional email assistant. Write concise, polite, business-style replies. Return valid JSON with fields subject, body, confidence.",
                model=self.model,
                temperature=0.7,
                max_tokens=900,
                feature="reply_drafting",
                session=None,
            )
            if result.get("success") and result.get("response"):
                reply_data = self._parse_json_object(result["response"]) or {}
                reply_body = (reply_data.get("body") or "").strip() or result["response"].strip()
                reply_subject = (reply_data.get("subject") or "").strip() or f"Re: {email_subject}"
                return {
                    "subject": reply_subject,
                    "body": reply_body,
                    "tone": tone,
                    "ai_generated": True,
                    "mock": False,
                    "confidence": reply_data.get("confidence", 0.85),
                    "model": result.get("model"),
                }
        except Exception as e:
            print(f"❌ [LLMService] Reply generation error: {e}, using fallback template")

        signer_name = self._extract_signer_name(user_name)
        mock_reply = self._generate_mock_reply(sender_name, email_subject, email_body, signer_name)
        return {
            "subject": mock_reply["subject"],
            "body": mock_reply["body"],
            "tone": tone,
            "ai_generated": False,
            "mock": True,
            "mock_warning": "AI service is temporarily unavailable. A safe template reply was generated instead.",
        }

    def _extract_sender_name(self, sender_email: str) -> str:
        try:
            display_name, parsed_email = parseaddr(sender_email or "")
            if display_name:
                cleaned_display = re.sub(r"[<>\"']", "", display_name).strip()
                if cleaned_display:
                    return cleaned_display

            name_part = (parsed_email or sender_email or "").split("@")[0]
            name_part = name_part.replace(".", " ").replace("_", " ").replace("-", " ")
            name_part = re.sub(r"[^A-Za-z0-9 ]+", " ", name_part)
            words = name_part.split()
            name = " ".join([word.capitalize() for word in words if word])
            return name if name else "there"
        except Exception:
            return "there"

    def _extract_signer_name(self, user_name: Optional[str]) -> str:
        value = (user_name or "").strip()
        return value if value else "Team"

    def _generate_mock_reply(self, sender_name: str, subject: str, body: str, signer_name: str) -> Dict[str, str]:
        body_lower = body.lower() if body else ""
        is_meeting_request = any(word in body_lower for word in ["meeting", "schedule", "calendar", "time", "availability"])
        is_question = "?" in body
        is_document_review = any(word in body_lower for word in ["document", "review", "feedback", "attached", "see attached"])

        if is_meeting_request:
            reply_body = (
                f"Dear {sender_name},\n\n"
                "Thank you for reaching out regarding the meeting request.\n\n"
                "I will review your availability and get back to you shortly.\n\n"
                f"Best regards,\n{signer_name}"
            )
        elif is_document_review:
            reply_body = (
                f"Dear {sender_name},\n\n"
                "Thank you for sending this over for review. I will review it and share feedback shortly.\n\n"
                f"Best regards,\n{signer_name}"
            )
        elif is_question:
            reply_body = (
                f"Dear {sender_name},\n\n"
                "Thank you for your question. I am reviewing your message and will respond shortly.\n\n"
                f"Best regards,\n{signer_name}"
            )
        else:
            reply_body = (
                f"Dear {sender_name},\n\n"
                f'Thank you for your email regarding "{subject}". I will review it and get back to you shortly.\n\n'
                f"Best regards,\n{signer_name}"
            )

        return {"subject": f"Re: {subject}", "body": reply_body}

    async def health_check(self) -> Dict[str, Any]:
        """Check LLM service health."""
        status = "healthy"
        details = []

        try:
            probe = await self.orchestrator.call_llm(
                prompt="Return OK",
                system_prompt="Health check",
                model=self.model,
                temperature=0.0,
                max_tokens=8,
                feature="health_check",
                session=None,
            )
            if not probe.get("success"):
                status = "degraded"
                details.append(f"LLM chain error: {probe.get('error')}")
        except Exception as e:
            status = "degraded"
            details.append(f"LLM chain error: {e}")

        return {
            "status": status,
            "provider": "auto",
            "model": self.model,
            "details": details,
            "mock_fallback_available": True,
        }
