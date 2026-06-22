"""
Daily AI briefing service.

Builds a per-user intelligence snapshot once per day and caches it.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import logger
from app.models.database import Email
from app.models.commitment_models import Commitment
from app.models.phase1_models import DailyBriefing, UserDigestPreference
from app.services.llm_orchestration_service import llm_service


class DailyBriefingService:
    async def get_or_create_preference(self, user_id: str, session: AsyncSession) -> UserDigestPreference:
        result = await session.execute(
            select(UserDigestPreference).where(UserDigestPreference.user_id == user_id)
        )
        pref = result.scalar_one_or_none()
        if pref:
            return pref

        pref = UserDigestPreference(user_id=user_id, timezone="UTC", send_hour=6, enabled=True)
        session.add(pref)
        await session.flush()
        return pref

    async def get_today_briefing(self, user_id: str, session: AsyncSession) -> Optional[DailyBriefing]:
        pref = await self.get_or_create_preference(user_id, session)
        local_tz = ZoneInfo(pref.timezone or "UTC")
        today_local = datetime.now(local_tz).date()

        result = await session.execute(
            select(DailyBriefing).where(
                and_(
                    DailyBriefing.user_id == user_id,
                    DailyBriefing.briefing_date == today_local,
                )
            )
        )
        return result.scalar_one_or_none()

    async def generate_daily_briefing(
        self,
        user_id: str,
        session: AsyncSession,
        target_date: Optional[date] = None,
        force_regenerate: bool = False,
    ) -> DailyBriefing:
        pref = await self.get_or_create_preference(user_id, session)
        local_tz = ZoneInfo(pref.timezone or "UTC")
        target_date = target_date or datetime.now(local_tz).date()

        existing_result = await session.execute(
            select(DailyBriefing).where(
                and_(
                    DailyBriefing.user_id == user_id,
                    DailyBriefing.briefing_date == target_date,
                )
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing and not force_regenerate:
            return existing

        context = await self._build_context(user_id=user_id, session=session)
        ai_result = await self._generate_ai_briefing(user_id=user_id, context=context, session=session)

        content = ai_result.get("content") if ai_result.get("success") else self._fallback_briefing(context)
        credits_used = 2 if ai_result.get("success") else 0

        if existing:
            existing.content = content
            existing.generated_at = datetime.utcnow()
            existing.credits_used = credits_used
            existing.status = "generated" if ai_result.get("success") else "failed"
            existing.error_message = ai_result.get("error")
            await session.flush()
            return existing

        briefing = DailyBriefing(
            user_id=user_id,
            briefing_date=target_date,
            content=content,
            generated_at=datetime.utcnow(),
            credits_used=credits_used,
            status="generated" if ai_result.get("success") else "failed",
            error_message=ai_result.get("error"),
        )
        session.add(briefing)
        await session.flush()
        return briefing

    async def _build_context(self, user_id: str, session: AsyncSession) -> Dict[str, Any]:
        now = datetime.utcnow()
        seven_days = now + timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)
        three_days_ago = now - timedelta(days=3)

        unresolved_result = await session.execute(
            select(Commitment)
            .where(
                and_(
                    Commitment.user_id == user_id,
                    Commitment.status.in_(["pending", "in_progress"]),
                )
            )
            .order_by(Commitment.deadline.asc().nulls_last())
            .limit(20)
        )
        unresolved_commitments = [c.to_dict() for c in unresolved_result.scalars().all()]

        negative_result = await session.execute(
            select(Email)
            .where(
                and_(
                    Email.user_id == user_id,
                    Email.sentiment == "negative",
                    Email.received_at >= thirty_days_ago,
                )
            )
            .order_by(Email.received_at.desc())
            .limit(20)
        )
        high_negative_emails = [e.to_dict() for e in negative_result.scalars().all()]

        upcoming_result = await session.execute(
            select(Commitment)
            .where(
                and_(
                    Commitment.user_id == user_id,
                    Commitment.status.in_(["pending", "in_progress"]),
                    Commitment.deadline.isnot(None),
                    Commitment.deadline >= now,
                    Commitment.deadline <= seven_days,
                )
            )
            .order_by(Commitment.deadline.asc())
            .limit(20)
        )
        upcoming_deadlines = [c.to_dict() for c in upcoming_result.scalars().all()]

        idle_threads_result = await session.execute(
            select(
                Email.thread_id,
                func.max(Email.received_at).label("last_activity_at"),
                func.count(Email.id).label("email_count"),
            )
            .where(
                and_(
                    Email.user_id == user_id,
                    Email.thread_id.isnot(None),
                    Email.thread_id != "",
                )
            )
            .group_by(Email.thread_id)
            .having(func.max(Email.received_at) <= three_days_ago)
            .order_by(func.max(Email.received_at).asc())
            .limit(25)
        )

        idle_threads: List[Dict[str, Any]] = []
        for row in idle_threads_result.all():
            idle_threads.append(
                {
                    "thread_id": row[0],
                    "last_activity_at": row[1].isoformat() if row[1] else None,
                    "email_count": int(row[2] or 0),
                }
            )

        return {
            "unresolved_commitments": unresolved_commitments,
            "high_sentiment_negative_emails": high_negative_emails,
            "idle_threads": idle_threads,
            "upcoming_deadlines": upcoming_deadlines,
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def _generate_ai_briefing(
        self,
        user_id: str,
        context: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        prompt = (
            "You are an executive assistant. Given JSON context, produce a strict JSON object with keys:\n"
            "overview (string), priorities (array of {title, reason, urgency}), risks (array of strings), "
            "follow_ups (array of {thread_or_email, action}), schedule (array of {item, date}), "
            "metrics (object with counts), raw_context_checksum (string).\n"
            "Use concise language. Do not include markdown.\n\n"
            f"Context JSON:\n{json.dumps(context, default=str)[:12000]}"
        )

        result = await llm_service.call_llm(
            prompt=prompt,
            model=getattr(settings, "LLM_MODEL", "qwen2.5-7b-instruct-q4_k_m-00001-of-00002"),
            temperature=0.2,
            max_tokens=1400,
            user_id=user_id,
            feature="summarization",
            session=session,
        )
        if not result.get("success"):
            return {"success": False, "error": result.get("error")}

        raw = (result.get("response") or "").strip()
        parsed = self._parse_json(raw)
        if isinstance(parsed, dict):
            return {"success": True, "content": parsed}

        return {
            "success": True,
            "content": {
                "overview": raw[:1200],
                "priorities": [],
                "risks": [],
                "follow_ups": [],
                "schedule": [],
                "metrics": {
                    "unresolved_commitments": len(context.get("unresolved_commitments", [])),
                    "high_sentiment_negative_emails": len(context.get("high_sentiment_negative_emails", [])),
                    "idle_threads": len(context.get("idle_threads", [])),
                    "upcoming_deadlines": len(context.get("upcoming_deadlines", [])),
                },
            },
        }

    def _fallback_briefing(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "overview": "Daily briefing generated without AI due to a temporary processing issue.",
            "priorities": [],
            "risks": [],
            "follow_ups": [],
            "schedule": [],
            "metrics": {
                "unresolved_commitments": len(context.get("unresolved_commitments", [])),
                "high_sentiment_negative_emails": len(context.get("high_sentiment_negative_emails", [])),
                "idle_threads": len(context.get("idle_threads", [])),
                "upcoming_deadlines": len(context.get("upcoming_deadlines", [])),
            },
            "context_snapshot": context,
        }

    @staticmethod
    def _parse_json(raw: str) -> Optional[Any]:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Try to recover JSON object embedded in prose
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                logger.warning("Failed to parse briefing JSON recovery payload")
        return None
