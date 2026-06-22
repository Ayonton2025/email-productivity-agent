"""
Auto follow-up service (Phase 1).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import logger
from app.models.database import Email, UserEmailAccount
from app.models.phase1_models import FollowUpExecution, FollowUpPolicy
from app.services.llm_orchestration_service import llm_service
from app.services.smtp_service import smtp_service


class FollowUpService:
    async def get_or_create_policy(self, user_id: str, session: AsyncSession) -> FollowUpPolicy:
        result = await session.execute(select(FollowUpPolicy).where(FollowUpPolicy.user_id == user_id))
        policy = result.scalar_one_or_none()
        if policy:
            return policy

        policy = FollowUpPolicy(
            user_id=user_id,
            enabled=True,
            min_delay_hours=48,
            max_stages=3,
            auto_send=False,
            tone_profile="professional",
        )
        session.add(policy)
        await session.flush()
        return policy

    async def schedule_follow_up(
        self,
        user_id: str,
        email_id: str,
        session: AsyncSession,
        delay_hours: Optional[int] = None,
    ) -> Email:
        email_result = await session.execute(
            select(Email).where(and_(Email.id == email_id, Email.user_id == user_id))
        )
        email = email_result.scalar_one_or_none()
        if not email:
            raise ValueError("Email not found")

        policy = await self.get_or_create_policy(user_id=user_id, session=session)
        delay = int(delay_hours if delay_hours is not None else policy.min_delay_hours)
        anchor = email.sent_at or email.received_at or datetime.utcnow()

        # Follow-up agent is intended for outbound messages.
        if (email.folder or "").lower() != "sent":
            raise ValueError("Only sent emails can be scheduled for follow-up")
        if not (email.recipients or []):
            raise ValueError("Source sent email has no recipients")

        email.last_sent_at = email.last_sent_at or anchor
        email.follow_up_enabled = True
        email.follow_up_scheduled_at = anchor + timedelta(hours=delay)
        await session.flush()
        return email

    async def process_due_followups(self, session: AsyncSession, limit: int = 100) -> Dict[str, int]:
        now = datetime.utcnow()
        stats = {"processed": 0, "queued_for_approval": 0, "auto_sent": 0, "skipped_replied": 0, "failed": 0}

        due_result = await session.execute(
            select(Email)
            .where(
                and_(
                    Email.follow_up_enabled == True,
                    Email.follow_up_scheduled_at.isnot(None),
                    Email.follow_up_scheduled_at <= now,
                )
            )
            .order_by(Email.follow_up_scheduled_at.asc())
            .limit(limit)
        )
        due_emails = list(due_result.scalars().all())

        for email in due_emails:
            try:
                policy = await self.get_or_create_policy(email.user_id, session)
                if not policy.enabled:
                    continue

                if await self._has_reply(email, session):
                    email.replied_at = datetime.utcnow()
                    email.follow_up_enabled = False
                    email.follow_up_scheduled_at = None
                    stats["skipped_replied"] += 1
                    continue

                current_stage = int(email.follow_up_stage or 0)
                next_stage = current_stage + 1
                if next_stage > int(policy.max_stages):
                    email.follow_up_enabled = False
                    email.follow_up_scheduled_at = None
                    continue

                existing_exec = await session.execute(
                    select(FollowUpExecution).where(
                        and_(
                            FollowUpExecution.source_email_id == email.id,
                            FollowUpExecution.stage == next_stage,
                            FollowUpExecution.status.in_(
                                ["pending_approval", "approved_sent", "auto_sent", "draft_saved"]
                            ),
                        )
                    )
                )
                if existing_exec.scalar_one_or_none():
                    email.follow_up_scheduled_at = None
                    continue

                draft_subject, draft_body = await self._generate_followup_content(email, policy, next_stage, session)
                execution = FollowUpExecution(
                    user_id=email.user_id,
                    source_email_id=email.id,
                    stage=next_stage,
                    scheduled_for=email.follow_up_scheduled_at or now,
                    generated_subject=draft_subject,
                    generated_body=draft_body,
                    status="pending_approval",
                    metadata_json={
                        "thread_id": email.thread_id,
                        "in_reply_to": email.message_id,
                        "references": email.references or [],
                    },
                )
                session.add(execution)
                await session.flush()

                if policy.auto_send:
                    ok, err = await self._send_execution(execution=execution, source_email=email, session=session)
                    if ok:
                        execution.status = "auto_sent"
                        execution.processed_at = datetime.utcnow()
                        email.follow_up_stage = next_stage
                        stats["auto_sent"] += 1
                        self._reschedule_or_close(email, policy)
                    else:
                        execution.status = "failed"
                        execution.error_message = err
                        stats["failed"] += 1
                else:
                    # Keep execution in approval queue and pause further scheduling until approved.
                    execution.status = "pending_approval"
                    email.follow_up_scheduled_at = None
                    stats["queued_for_approval"] += 1

                stats["processed"] += 1
            except Exception as e:
                logger.error("Failed processing follow-up for email %s: %s", email.id, str(e))
                stats["failed"] += 1

        return stats

    async def list_queue(
        self,
        user_id: str,
        session: AsyncSession,
        status: str = "pending_approval",
        limit: int = 50,
    ) -> List[FollowUpExecution]:
        result = await session.execute(
            select(FollowUpExecution)
            .where(
                and_(
                    FollowUpExecution.user_id == user_id,
                    FollowUpExecution.status == status,
                )
            )
            .order_by(FollowUpExecution.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def approve_execution(self, user_id: str, execution_id: str, session: AsyncSession) -> FollowUpExecution:
        execution_result = await session.execute(
            select(FollowUpExecution).where(
                and_(
                    FollowUpExecution.id == execution_id,
                    FollowUpExecution.user_id == user_id,
                )
            )
        )
        execution = execution_result.scalar_one_or_none()
        if not execution:
            raise ValueError("Follow-up queue item not found")

        if execution.status != "pending_approval":
            return execution

        source_result = await session.execute(
            select(Email).where(
                and_(
                    Email.id == execution.source_email_id,
                    Email.user_id == user_id,
                )
            )
        )
        source_email = source_result.scalar_one_or_none()
        if not source_email:
            execution.status = "failed"
            execution.error_message = "Source email missing"
            await session.flush()
            return execution

        policy = await self.get_or_create_policy(user_id=user_id, session=session)
        ok, err = await self._send_execution(execution=execution, source_email=source_email, session=session)
        if ok:
            execution.status = "approved_sent"
            execution.processed_at = datetime.utcnow()
            source_email.follow_up_stage = int(execution.stage or 1)
            self._reschedule_or_close(source_email, policy)
        else:
            execution.status = "failed"
            execution.error_message = err
        await session.flush()
        return execution

    async def _has_reply(self, source_email: Email, session: AsyncSession) -> bool:
        if not source_email.thread_id:
            return False

        outbound_time = source_email.last_sent_at or source_email.sent_at or source_email.received_at
        if not outbound_time:
            return False

        reply_result = await session.execute(
            select(Email)
            .where(
                and_(
                    Email.user_id == source_email.user_id,
                    Email.thread_id == source_email.thread_id,
                    Email.received_at > outbound_time,
                    Email.folder != "Sent",
                )
            )
            .order_by(Email.received_at.asc())
            .limit(1)
        )
        return reply_result.scalar_one_or_none() is not None

    async def _generate_followup_content(
        self,
        email: Email,
        policy: FollowUpPolicy,
        stage: int,
        session: AsyncSession,
    ) -> Tuple[str, str]:
        thread_context = (
            f"Original subject: {email.subject or ''}\n"
            f"Original body:\n{(email.body_text or email.body_html or '')[:5000]}\n\n"
            f"Stage: {stage}\n"
            f"Tone: {policy.tone_profile}\n"
            "Write a short follow-up email that references the prior message and asks for a response."
        )

        result = await llm_service.call_llm(
            prompt=(
                "Return strict JSON with keys `subject` and `body` only. "
                "Keep body under 120 words.\n\n"
                + thread_context
            ),
            model=getattr(settings, "LLM_MODEL", "qwen2.5-7b-instruct-q4_k_m-00001-of-00002"),
            temperature=0.4,
            max_tokens=420,
            user_id=email.user_id,
            feature="reply_drafting",
            session=session,
        )

        if not result.get("success"):
            raise ValueError(result.get("error", "Failed to generate follow-up"))

        raw = (result.get("response") or "").strip()
        parsed = self._parse_json(raw)
        if isinstance(parsed, dict):
            subject = str(parsed.get("subject") or "").strip()
            body = str(parsed.get("body") or "").strip()
            if subject and body:
                return subject, body

        fallback_subject = f"Re: {email.subject or 'Quick follow-up'}"
        return fallback_subject, raw[:4000]

    async def _send_execution(
        self,
        execution: FollowUpExecution,
        source_email: Email,
        session: AsyncSession,
    ) -> Tuple[bool, str]:
        account_result = await session.execute(
            select(UserEmailAccount).where(UserEmailAccount.id == source_email.account_id)
        )
        account = account_result.scalar_one_or_none()
        if not account:
            return False, "Source account not found"

        recipients = source_email.recipients or []
        if not recipients:
            return False, "Source email has no recipient to follow up with"

        target = recipients[0]
        refs = list(source_email.references or [])
        if source_email.message_id and source_email.message_id not in refs:
            refs.append(source_email.message_id)

        sent, message = await smtp_service.send_email(
            account=account,
            db=session,
            to=target,
            subject=execution.generated_subject or f"Re: {source_email.subject or ''}",
            body_text=execution.generated_body or "",
            in_reply_to=source_email.message_id,
            references=refs,
        )
        return sent, message

    def _reschedule_or_close(self, email: Email, policy: FollowUpPolicy) -> None:
        if int(email.follow_up_stage or 0) >= int(policy.max_stages):
            email.follow_up_enabled = False
            email.follow_up_scheduled_at = None
            return

        delay_hours = max(1, int(policy.min_delay_hours or 48))
        email.follow_up_scheduled_at = datetime.utcnow() + timedelta(hours=delay_hours)
        email.last_sent_at = datetime.utcnow()

    @staticmethod
    def _parse_json(raw: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(raw[start : end + 1])
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                return None
        return None
