"""
AI processing for synced emails:
- Categorization (ai_category)
- Summary (ai_summary)
- Action item extraction (action_items)
- Priority (priority)
- Relationship Intelligence (contacts, companies, sentiment)
- Decision Intelligence (commitments, risks, opportunities)

This is designed to be safe:
- If no LLM API key is configured, it falls back to LLMService mock mode.
- If parsing fails, it stores best-effort outputs and never blocks inbox rendering.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.config import settings
from app.models.database import Email
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService
from app.services.relationship_service import RelationshipService
from app.services.decision_intelligence import DecisionIntelligenceService


DEFAULT_CATEGORIES = [
    "Important",
    "To-Do",
    "Work",
    "Personal",
    "Finance",
    "Travel",
    "Newsletter",
    "Spam",
    "Uncategorized",
]


def _safe_json_loads(s: str) -> Optional[Any]:
    try:
        return json.loads(s)
    except Exception:
        return None


def _normalize_category(raw: str) -> str:
    if not raw:
        return "Uncategorized"
    raw = raw.strip().strip('"').strip()
    # If model returned something like {"category":"X"}
    parsed = _safe_json_loads(raw)
    if isinstance(parsed, dict) and "category" in parsed:
        raw = str(parsed.get("category") or "").strip()
    # Canonicalize to known set when possible
    for c in DEFAULT_CATEGORIES:
        if raw.lower() == c.lower():
            return c
    # Allow user-defined categories too; keep as-is but not empty
    return raw or "Uncategorized"


def _infer_priority(category: str, action_items: List[Dict[str, Any]]) -> str:
    cat = (category or "").lower()
    if cat in {"important", "urgent"}:
        return "high"
    if cat in {"to-do", "todo", "finance"}:
        return "medium" if action_items else "medium"
    if cat in {"spam"}:
        return "low"
    if cat in {"newsletter"}:
        return "low"
    return "medium"


async def process_email_ai(db: AsyncSession, email: Email) -> None:
    """
    Process a single Email row in-place (updates ai fields).
    Now includes Relationship Intelligence and Decision Intelligence.
    """
    if not getattr(settings, "ENABLE_AI_PROCESSING", True):
        return

    llm = LLMService()
    prompts = PromptService(db)

    categorization_prompt = await prompts.get_active_prompt("categorization")
    summary_prompt = await prompts.get_active_prompt("summary")
    action_prompt = await prompts.get_active_prompt("action_extraction")

    email_content = (
        f"From: {email.sender}\n"
        f"Subject: {email.subject}\n"
        f"Body: {(email.body_text or email.body_html or '')[:8000]}"
    )

    # Run in parallel; each call has its own fallback behavior in LLMService.
    tasks = []
    tasks.append(llm.process_prompt(categorization_prompt.template if categorization_prompt else "Categorize this email.", email_content))
    tasks.append(llm.process_prompt(summary_prompt.template if summary_prompt else "Summarize this email.", email_content))
    tasks.append(llm.process_prompt(action_prompt.template if action_prompt else "Extract action items as JSON.", email_content))

    category_raw, summary_raw, actions_raw = await asyncio.gather(*tasks, return_exceptions=True)

    # Category
    if isinstance(category_raw, Exception):
        category = email.ai_category or "Uncategorized"
    else:
        category = _normalize_category(str(category_raw))

    # Summary
    if isinstance(summary_raw, Exception):
        summary = email.ai_summary
    else:
        summary = str(summary_raw).strip()

    # Action items
    action_items: List[Dict[str, Any]] = []
    if not isinstance(actions_raw, Exception):
        parsed = _safe_json_loads(str(actions_raw).strip())
        if isinstance(parsed, dict) and "tasks" in parsed and isinstance(parsed["tasks"], list):
            action_items = parsed["tasks"]
        elif isinstance(parsed, list):
            action_items = parsed
        elif isinstance(parsed, dict) and "action_items" in parsed and isinstance(parsed["action_items"], list):
            action_items = parsed["action_items"]

    email.ai_category = category
    email.ai_summary = summary
    email.action_items = action_items
    email.priority = _infer_priority(category, action_items)
    
    # Extract sentiment if not already set
    if not email.sentiment:
        try:
            sentiment_prompt = "Analyze the sentiment of this email. Respond with only one word: positive, neutral, or negative.\n\n" + email_content
            sentiment_raw = await llm.process_prompt(sentiment_prompt, "")
            if not isinstance(sentiment_raw, Exception):
                sentiment = str(sentiment_raw).strip().lower()
                if sentiment in ["positive", "neutral", "negative"]:
                    email.sentiment = sentiment
        except Exception:
            pass  # Don't fail if sentiment extraction fails
    
    # Process Relationship Intelligence (non-blocking)
    try:
        relationship_service = RelationshipService(db)
        relationship_data = await relationship_service.process_email_for_relationships(email)
        # Relationship data is stored in Contact/Company tables, not in Email
    except Exception as e:
        print(f"⚠️ [process_email_ai] Relationship processing failed: {e}")
    
    # Process Decision Intelligence (non-blocking)
    try:
        decision_service = DecisionIntelligenceService(db)
        decision_data = await decision_service.process_email_for_decisions(email)
        # Decision data is stored in Commitment/Risk/Opportunity tables
    except Exception as e:
        print(f"⚠️ [process_email_ai] Decision intelligence processing failed: {e}")
    
    email.processing_status = "completed"


async def process_emails_ai(db: AsyncSession, email_ids: List[str]) -> int:
    """
    Process a batch of emails by ID with bounded concurrency.
    Returns number processed.
    """
    if not email_ids:
        return 0

    # Limit concurrency to avoid rate limits / latency spikes.
    sem = asyncio.Semaphore(3)

    async def _run_one(eid: str) -> bool:
        async with sem:
            result = await db.execute(select(Email).where(Email.id == eid))
            email = result.scalar_one_or_none()
            if not email:
                return False
            try:
                await process_email_ai(db, email)
                return True
            except Exception:
                # Never fail the whole batch
                email.processing_status = "failed"
                return False

    results = await asyncio.gather(*[_run_one(eid) for eid in email_ids])
    await db.commit()
    return sum(1 for r in results if r)

