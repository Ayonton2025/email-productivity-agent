"""
Hosted email abuse prevention:
- Daily send limits
- Domain throttling
- Spam/risk scoring (heuristic + optional AI)
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import logger
from app.models.database import UserEmailAccount
from app.models.hosted_email_models import HostedEmailSendLog
from app.services.llm_orchestration_service import llm_service


LINK_REGEX = re.compile(r"https?://", flags=re.IGNORECASE)
WORD_REGEX = re.compile(r"[a-zA-Z]+")


class HostedEmailAbuseService:
    async def evaluate_send_permission(
        self,
        session: AsyncSession,
        account: UserEmailAccount,
        to: str,
        subject: str,
        body_text: str,
    ) -> Dict[str, Any]:
        """
        Returns:
        {
          "allowed": bool,
          "reason": str|None,
          "spam_score": float,
          "link_count": int,
          "ai_flagged": bool
        }
        """
        now = datetime.utcnow()
        day_start = datetime(now.year, now.month, now.day)
        day_end = day_start + timedelta(days=1)

        if account.send_count_reset_at and account.send_count_reset_at < day_start:
            account.send_count_daily = 0
            account.send_count_reset_at = day_end
        elif not account.send_count_reset_at:
            account.send_count_reset_at = day_end

        account_daily_limit = int(account.send_limit_daily or settings.HOSTED_EMAIL_DAILY_SEND_LIMIT or 0)
        if account_daily_limit > 0 and int(account.send_count_daily or 0) >= account_daily_limit:
            return {
                "allowed": False,
                "reason": "Daily account send limit exceeded",
                "spam_score": 1.0,
                "link_count": self._count_links(body_text),
                "ai_flagged": False,
            }

        recipients_today_q = await session.execute(
            select(func.count(func.distinct(HostedEmailSendLog.recipient_email))).where(
                and_(
                    HostedEmailSendLog.account_id == account.id,
                    HostedEmailSendLog.created_at >= day_start,
                    HostedEmailSendLog.created_at < day_end,
                    HostedEmailSendLog.blocked == False,
                )
            )
        )
        unique_recipients_today = int(recipients_today_q.scalar_one() or 0)
        recipient_limit = int(settings.HOSTED_EMAIL_MAX_RECIPIENTS_PER_DAY or 0)
        if recipient_limit > 0 and unique_recipients_today >= recipient_limit:
            return {
                "allowed": False,
                "reason": "Daily unique recipient limit exceeded",
                "spam_score": 1.0,
                "link_count": self._count_links(body_text),
                "ai_flagged": False,
            }

        sender_domain = self._extract_domain(account.email)
        if sender_domain:
            domain_count_q = await session.execute(
                select(func.count(HostedEmailSendLog.id)).where(
                    and_(
                        HostedEmailSendLog.sender_domain == sender_domain,
                        HostedEmailSendLog.created_at >= day_start,
                        HostedEmailSendLog.created_at < day_end,
                        HostedEmailSendLog.blocked == False,
                    )
                )
            )
            domain_count = int(domain_count_q.scalar_one() or 0)
            domain_daily_limit = int(settings.HOSTED_EMAIL_DOMAIN_DAILY_SEND_LIMIT or 0)
            if domain_daily_limit > 0 and domain_count >= domain_daily_limit:
                return {
                    "allowed": False,
                    "reason": "Domain daily throttle exceeded",
                    "spam_score": 1.0,
                    "link_count": self._count_links(body_text),
                    "ai_flagged": False,
                }

        score, signals = self._heuristic_spam_score(subject=subject, body_text=body_text)
        ai_flagged = False
        if settings.HOSTED_EMAIL_ABUSE_USE_AI and settings.is_llm_configured():
            ai_risk = await self._ai_spam_risk_score(
                user_id=account.user_id,
                subject=subject,
                body_text=body_text,
                session=session,
            )
            if ai_risk is not None:
                score = max(score, ai_risk)
                ai_flagged = ai_risk >= float(settings.HOSTED_EMAIL_SPAM_SCORE_BLOCK_THRESHOLD or 0.75)

        threshold = float(settings.HOSTED_EMAIL_SPAM_SCORE_BLOCK_THRESHOLD or 0.75)
        return {
            "allowed": score < threshold,
            "reason": None if score < threshold else f"Spam/risk score {score:.2f} exceeds threshold {threshold:.2f}",
            "spam_score": score,
            "link_count": signals["link_count"],
            "ai_flagged": ai_flagged,
        }

    async def record_send_attempt(
        self,
        session: AsyncSession,
        account: UserEmailAccount,
        to: str,
        subject: str,
        body_text: str,
        blocked: bool,
        block_reason: Optional[str],
        spam_score: float,
        ai_flagged: bool = False,
        link_count: Optional[int] = None,
    ) -> HostedEmailSendLog:
        sender_domain = self._extract_domain(account.email)
        recipient_domain = self._extract_domain(to)
        if link_count is None:
            link_count = self._count_links(body_text)

        log = HostedEmailSendLog(
            user_id=account.user_id,
            account_id=account.id,
            sender_email=account.email,
            sender_domain=sender_domain or "",
            recipient_email=to,
            recipient_domain=recipient_domain or "",
            subject_hash=self._hash_text(subject),
            body_hash=self._hash_text((body_text or "")[:5000]),
            link_count=link_count,
            spam_score=spam_score,
            blocked=blocked,
            block_reason=block_reason,
            ai_flagged=ai_flagged,
        )
        session.add(log)

        if not blocked:
            account.send_count_daily = int(account.send_count_daily or 0) + 1
            now = datetime.utcnow()
            next_day = datetime(now.year, now.month, now.day) + timedelta(days=1)
            account.send_count_reset_at = next_day

        await session.flush()
        return log

    def _heuristic_spam_score(self, subject: str, body_text: str) -> Tuple[float, Dict[str, Any]]:
        subject = subject or ""
        body_text = body_text or ""
        lower = f"{subject}\n{body_text}".lower()

        keyword_hits = 0
        for kw in settings.get_hosted_spam_keywords():
            if kw and kw in lower:
                keyword_hits += 1

        link_count = self._count_links(body_text)
        words = WORD_REGEX.findall(body_text)
        upper_ratio = 0.0
        if words:
            upper_words = [w for w in words if len(w) >= 4 and w.upper() == w]
            upper_ratio = len(upper_words) / max(1, len(words))

        score = 0.0
        score += min(0.5, keyword_hits * 0.12)
        score += min(0.35, max(0, link_count - 2) * 0.06)
        score += min(0.2, upper_ratio * 0.8)

        max_links = int(settings.HOSTED_EMAIL_MAX_LINKS_PER_EMAIL or 8)
        if link_count > max_links:
            score = max(score, 0.9)

        return min(1.0, score), {"keyword_hits": keyword_hits, "link_count": link_count, "upper_ratio": upper_ratio}

    async def _ai_spam_risk_score(
        self,
        user_id: str,
        subject: str,
        body_text: str,
        session: AsyncSession,
    ) -> Optional[float]:
        prompt = (
            "Classify risk that this outbound email is abusive/spam. "
            "Return strict JSON: {\"risk_score\": 0.0-1.0, \"reason\": \"...\"}\n\n"
            f"Subject: {subject}\nBody:\n{body_text[:3500]}"
        )
        result = await llm_service.call_llm(
            prompt=prompt,
            model=getattr(settings, "LLM_MODEL", "qwen2.5-7b-instruct-q4_k_m-00001-of-00002"),
            temperature=0.0,
            max_tokens=200,
            user_id=user_id,
            feature="risk_analysis",
            session=session,
        )
        if not result.get("success"):
            return None

        raw = (result.get("response") or "").strip()
        match = re.search(r"([01](?:\.\d+)?)", raw)
        if match:
            try:
                val = float(match.group(1))
                return max(0.0, min(1.0, val))
            except Exception:
                return None
        return None

    @staticmethod
    def _extract_domain(email: str) -> Optional[str]:
        if not email or "@" not in email:
            return None
        return email.split("@", 1)[1].strip().lower()

    @staticmethod
    def _hash_text(value: str) -> str:
        return hashlib.sha256((value or "").encode("utf-8")).hexdigest()

    @staticmethod
    def _count_links(body_text: str) -> int:
        return len(LINK_REGEX.findall(body_text or ""))
