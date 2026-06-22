"""
Auto-reply service: rule engine + draft generation.

- Fetches active rules (priority-ordered), checks away mode, matches category/sender.
- Generates reply via LLM, optionally enforces confidence threshold.
- Creates drafts with metadata (auto_reply, rule_id, approval_status) and optionally auto-sends via Gmail API.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auto_reply_models import AutoReplyRule, AwayModeSetting
from app.models.database import Email
from app.services.email_service import EmailService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

AUTO_REPLY_PROMPT = """Write a polite, professional auto-reply to this email.

Return valid JSON only, with exactly two keys:
- "body": string, the full reply body (including greeting and sign-off).
- "confidence": number between 0 and 1 (how confident you are this reply is appropriate).

Example: {"body": "Dear ...\\n\\n...\\n\\nBest regards,\\n[Name]", "confidence": 0.9}

Incoming email:
From: {sender}
Subject: {subject}
Body:
{body}
"""


def _naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def get_away_mode(db: AsyncSession, user_id: str) -> bool:
    """Return True if user has away mode on and we're within any time window."""
    result = await db.execute(
        select(AwayModeSetting).where(AwayModeSetting.user_id == user_id)
    )
    setting = result.scalar_one_or_none()
    if not setting or not setting.is_active:
        return False
    now = datetime.now(timezone.utc)
    vf = _naive_utc(setting.valid_from)
    vu = _naive_utc(setting.valid_until)
    if vf is not None and now < vf:
        return False
    if vu is not None and now > vu:
        return False
    return True


def _parse_llm_reply(raw: str) -> Tuple[str, float]:
    """Parse LLM JSON {body, confidence}. Return (body, confidence); fallback (raw, 1.0)."""
    raw = (raw or "").strip()
    try:
        # Handle markdown code blocks
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        obj = json.loads(raw)
        body = obj.get("body") or obj.get("reply") or raw
        conf = float(obj.get("confidence", 1.0))
        conf = max(0.0, min(1.0, conf))
        return (str(body).strip(), conf)
    except Exception:
        return (raw, 1.0)


class AutoReplyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.email_service = EmailService(db)
        self.llm_service = LLMService()

    async def get_active_rules(self, user_id: str) -> List[AutoReplyRule]:
        result = await self.db.execute(
            select(AutoReplyRule)
            .where(AutoReplyRule.user_id == user_id)
            .where(AutoReplyRule.is_active == True)
            .order_by(AutoReplyRule.priority.asc(), AutoReplyRule.created_at.asc())
        )
        return list(result.scalars().all())

    def rule_matches(self, rule: AutoReplyRule, email: Dict[str, Any]) -> bool:
        cat = (email.get("ai_category") or email.get("category") or "").strip()
        if rule.match_category and rule.match_category.strip().lower() != cat.lower():
            return False
        sender = (email.get("sender") or "").lower()
        match_sender = (rule.match_sender or "").strip().lower()
        if match_sender and match_sender not in sender:
            return False
        return True

    async def process_email_for_auto_reply(
        self,
        email: Dict[str, Any],
        user_id: str,
        *,
        account_id: Optional[str] = None,
        account_provider: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        If away mode is required, check it first. Then find first matching rule (by priority),
        generate reply, enforce confidence_min, create draft (and optionally auto-send).
        Returns created draft dict or None.
        """
        rules = await self.get_active_rules(user_id)
        if not rules:
            return None

        away = await get_away_mode(self.db, user_id)
        for rule in rules:
            if rule.require_away_mode and not away:
                continue
            if not self.rule_matches(rule, email):
                continue
            try:
                draft = await self._generate_and_store(
                    email, rule, user_id,
                    account_id=account_id,
                    account_provider=account_provider,
                )
                return draft
            except Exception as e:
                logger.warning("Auto-reply generation failed for rule %s: %s", rule.id, e)
                continue
        return None

    async def _generate_and_store(
        self,
        email: Dict[str, Any],
        rule: AutoReplyRule,
        user_id: str,
        *,
        account_id: Optional[str] = None,
        account_provider: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        system_prompt = (
            "You are an automatic email assistant. Write polite, professional auto-replies. "
            "User instructions: " + (rule.instructions or "None")
        )
        body_raw = email.get("body_text") or email.get("body") or email.get("body_html") or ""
        if len(body_raw) > 8000:
            body_raw = body_raw[:8000] + "\n[... truncated]"
        content = AUTO_REPLY_PROMPT.format(
            sender=email.get("sender", ""),
            subject=email.get("subject", ""),
            body=body_raw,
        )
        raw = await self.llm_service.process_prompt(
            "Write the auto-reply email. Return JSON with 'body' and 'confidence'.",
            content,
            system_message=system_prompt,
        )
        reply_body, confidence = _parse_llm_reply(raw)
        if confidence < (rule.confidence_min or 0.0):
            logger.info(
                "Auto-reply skipped: confidence %.2f < min %.2f for rule %s",
                confidence, rule.confidence_min or 0.0, rule.id,
            )
            return None

        approval_status = "pending" if rule.use_approval_queue else "approved"
        metadata: Dict[str, Any] = {
            "auto_reply": True,
            "rule_id": rule.id,
            "confidence": confidence,
            "approval_status": approval_status,
        }
        if account_id:
            metadata["account_id"] = account_id
        if account_provider:
            metadata["account_provider"] = account_provider

        draft_data = {
            "subject": "Re: " + (email.get("subject") or "").strip().lstrip("Re: "),
            "body": reply_body,
            "recipient": email.get("sender"),
            "context_email_id": email.get("id"),
            "metadata": metadata,
        }
        draft = await self.email_service.create_draft(draft_data, user_id=user_id)

        if rule.auto_send and account_provider == "gmail" and account_id:
            sent = await self._auto_send_via_gmail(
                user_id=user_id,
                account_id=account_id,
                draft=draft,
                email=email,
            )
            if sent:
                metadata["auto_sent"] = True
                # Update draft metadata (e.g. mark as sent) – optional; we keep draft for audit.

        return draft

    async def _auto_send_via_gmail(
        self,
        user_id: str,
        account_id: str,
        draft: Dict[str, Any],
        email: Dict[str, Any],
    ) -> bool:
        """Send the draft via Gmail API. Returns True if sent successfully."""
        try:
            from app.services.gmail_send_service import send_via_gmail_api
            await send_via_gmail_api(
                db=self.db,
                user_id=user_id,
                to=draft.get("recipient") or email.get("sender"),
                subject=draft.get("subject", ""),
                body=draft.get("body", ""),
                thread_id=email.get("thread_id"),
                in_reply_to=email.get("message_id"),
                references=email.get("references") or [],
            )
            return True
        except Exception as e:
            logger.warning("Gmail auto-send failed: %s", e)
            return False
