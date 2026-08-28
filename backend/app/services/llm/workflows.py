"""Business-level structured LLM workflows."""

import json
import re
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .prompt_registry import PromptRegistry


class StructuredWorkflowMixin:
    def _extract_json(self, raw_text: str) -> Optional[Dict[str, Any]]:
        if not raw_text:
            return None
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            pass
        m = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None

    async def create_workspace_assist(
        self,
        page: str,
        objective: str,
        mode: str = "draft",
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        schema = self._assist_schema_for_page(page)
        prompt = f"Page:{page}\nMode:{mode}\nObjective:{objective}\nContext:{json.dumps(context or {}, ensure_ascii=True)}\nReturn JSON:\n{schema}"
        result = await self.call_llm(
            prompt=prompt,
            system_prompt="Generate structured JSON only.",
            model=self.default_model,
            user_id=user_id,
            feature=f"workspace_assist_{page}",
            session=session,
            temperature=0.4,
            max_tokens=1200,
        )
        if not result.get("success"):
            return {"success": False, "error": result.get("error", "Unknown LLM error")}
        parsed = self._extract_json(result.get("response", ""))
        if not parsed:
            return {
                "success": True,
                "page": page,
                "assistant_message": "I could not format a structured plan. Please refine your objective.",
                "suggested_actions": [],
                "draft": {},
                "raw_response": result.get("response", ""),
                "provider": result.get("provider"),
                "model": result.get("model"),
            }
        parsed["success"] = True
        parsed["provider"] = result.get("provider")
        parsed["model"] = result.get("model")
        return parsed

    def _assist_schema_for_page(self, page: str) -> str:
        p = (page or "").lower()
        if p == "campaigns":
            return json.dumps(
                {
                    "page": "campaigns",
                    "assistant_message": "string",
                    "suggested_actions": ["string"],
                    "draft": {
                        "campaign": {"name": "string"},
                        "sequences": [{"name": "string", "subject_template": "string", "body_template": "string"}],
                        "leads": [{"email": "string"}],
                    },
                }
            )
        if p == "workflows":
            return json.dumps(
                {
                    "page": "workflows",
                    "assistant_message": "string",
                    "suggested_actions": ["string"],
                    "draft": {
                        "workflow": {"name": "string", "trigger_type": "email_received"},
                        "steps": [{"name": "string", "step_type": "action"}],
                    },
                }
            )
        if p == "agents":
            return json.dumps(
                {
                    "page": "agents",
                    "assistant_message": "string",
                    "suggested_actions": ["string"],
                    "draft": {"agent": {"name": "string", "agent_type": "support", "system_prompt": "string"}},
                }
            )
        if p in {"prompts", "prompt_brain"}:
            return json.dumps(
                {
                    "page": "prompts",
                    "assistant_message": "string",
                    "suggested_actions": ["string"],
                    "draft": {"prompt": {"name": "string", "template": "string", "category": "analysis"}},
                }
            )
        return json.dumps(
            {"page": p or "general", "assistant_message": "string", "suggested_actions": ["string"], "draft": {}}
        )

    async def classify_email(
        self,
        sender: str,
        subject: str,
        body: str,
        tenant_id: str,
        user_id: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        r = await self.call_llm(
            prompt=f"From:{sender}\nSubject:{subject}\nBody:{body[:2000]}",
            system_prompt=PromptRegistry.get_prompt("email_classifier").get("system_prompt"),
            model=self.default_model,
            user_id=user_id,
            feature="categorization",
            session=session,
        )
        if not r.get("success"):
            return {"error": r.get("error")}
        try:
            c = json.loads(r["response"])
            return {
                "category": c.get("category"),
                "confidence": c.get("confidence"),
                "reasoning": c.get("reasoning"),
                "cost": r["cost"],
            }
        except json.JSONDecodeError:
            return {"error": "Failed to parse classification", "raw_response": r.get("response")}

    async def extract_actions(
        self, email_body: str, user_id: Optional[str] = None, session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        r = await self.call_llm(
            prompt=f"Extract action items:\n{email_body[:3000]}",
            system_prompt=PromptRegistry.get_prompt("action_extractor").get("system_prompt"),
            model=self.default_model,
            user_id=user_id,
            feature="action_extraction",
            session=session,
        )
        if not r.get("success"):
            return {"error": r.get("error")}
        try:
            a = json.loads(r["response"])
            return {"actions": a.get("actions", []), "cost": r["cost"]}
        except json.JSONDecodeError:
            return {"error": "Failed to parse actions"}

    async def analyze_sentiment(
        self, email_body: str, user_id: Optional[str] = None, session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        r = await self.call_llm(
            prompt=f"Analyze sentiment:\n{email_body[:2000]}",
            system_prompt=PromptRegistry.get_prompt("sentiment_analyzer").get("system_prompt"),
            model=self.default_model,
            user_id=user_id,
            feature="sentiment_analysis",
            session=session,
        )
        if not r.get("success"):
            return {"error": r.get("error")}
        try:
            s = json.loads(r["response"])
            return {
                "sentiment": s.get("sentiment"),
                "tone": s.get("tone"),
                "confidence": s.get("confidence"),
                "cost": r["cost"],
            }
        except json.JSONDecodeError:
            return {"error": "Failed to parse sentiment"}

    async def summarize_thread(
        self, thread_body: str, user_id: Optional[str] = None, session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        r = await self.call_llm(
            prompt=f"Summarize thread:\n{thread_body[:4000]}",
            system_prompt=PromptRegistry.get_prompt("email_summarizer").get("system_prompt"),
            model=self.default_model,
            user_id=user_id,
            feature="summarization",
            session=session,
        )
        if not r.get("success"):
            return {"error": r.get("error")}
        try:
            s = json.loads(r["response"])
            return {"summary": s.get("summary"), "key_points": s.get("key_points", []), "cost": r["cost"]}
        except json.JSONDecodeError:
            return {"error": "Failed to parse summary"}

    async def generate_reply(
        self, email_body: str, user_id: Optional[str] = None, session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        r = await self.call_llm(
            prompt=f"Generate reply:\n{email_body[:2000]}",
            system_prompt=PromptRegistry.get_prompt("reply_generator").get("system_prompt"),
            model=self.default_model,
            user_id=user_id,
            feature="reply_drafting",
            session=session,
            temperature=0.7,
        )
        if not r.get("success"):
            return {"error": r.get("error")}
        try:
            d = json.loads(r["response"])
            return {"reply": d.get("reply"), "tone": d.get("tone"), "cost": r["cost"]}
        except json.JSONDecodeError:
            return {"error": "Failed to parse reply"}

    async def score_relationship(
        self, email_history: str, user_id: Optional[str] = None, session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        r = await self.call_llm(
            prompt=f"Score relationship:\n{email_history[:3000]}",
            system_prompt=PromptRegistry.get_prompt("relationship_scorer").get("system_prompt"),
            model=self.default_model,
            user_id=user_id,
            feature="relationship_scoring",
            session=session,
        )
        if not r.get("success"):
            return {"error": r.get("error")}
        try:
            d = json.loads(r["response"])
            return {
                "relationship_score": d.get("relationship_score"),
                "relationship_type": d.get("relationship_type"),
                "engagement_level": d.get("engagement_level"),
                "cost": r["cost"],
            }
        except json.JSONDecodeError:
            return {"error": "Failed to parse relationship score"}
