"""
Hosted email provider integration service (Option A).

Provisioning is API-driven and provider-agnostic with env-based configuration.
"""

from __future__ import annotations

import re
import secrets
import string
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import httpx
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import encrypt_credential, logger
from app.models.database import UserEmailAccount
from app.models.hosted_email_models import HostedMailboxProvisioning


LOCAL_PART_REGEX = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{1,30}[a-z0-9])?$")


@dataclass
class ProvisionResult:
    success: bool
    external_reference: Optional[str]
    response_payload: Dict[str, Any]
    error: Optional[str] = None


class BaseHostedProviderClient(ABC):
    @abstractmethod
    async def provision_mailbox(
        self,
        email: str,
        password: str,
        display_name: Optional[str],
        quota_mb: int,
    ) -> ProvisionResult:
        raise NotImplementedError

    async def check_mailbox_available(self, email: str) -> Optional[bool]:
        return None


class MockHostedProviderClient(BaseHostedProviderClient):
    async def provision_mailbox(
        self,
        email: str,
        password: str,
        display_name: Optional[str],
        quota_mb: int,
    ) -> ProvisionResult:
        return ProvisionResult(
            success=True,
            external_reference=f"mock-{email}",
            response_payload={
                "provider": "mock",
                "email": email,
                "display_name": display_name,
                "quota_mb": quota_mb,
            },
        )


class MailcowHostedProviderClient(BaseHostedProviderClient):
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = settings.HOSTED_EMAIL_API_TIMEOUT_SECONDS

    async def provision_mailbox(
        self,
        email: str,
        password: str,
        display_name: Optional[str],
        quota_mb: int,
    ) -> ProvisionResult:
        if "@" not in email:
            return ProvisionResult(False, None, {}, error="Invalid email")
        local_part, domain = email.split("@", 1)
        payload = {
            "local_part": local_part,
            "domain": domain,
            "name": display_name or local_part,
            "password": password,
            "password2": password,
            "quota": str(quota_mb),
            "active": "1",
        }
        headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        url = f"{self.base_url}/api/v1/add/mailbox"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload, headers=headers)
            data = self._json_or_text(resp)
            if resp.status_code >= 400:
                return ProvisionResult(False, None, data, error=f"HTTP {resp.status_code}")

            ref = None
            if isinstance(data, dict):
                ref = data.get("id") or data.get("reference") or data.get("data")
            elif isinstance(data, list) and data:
                first = data[0]
                if isinstance(first, dict):
                    ref = first.get("id") or first.get("reference")
            return ProvisionResult(True, str(ref) if ref else None, data if isinstance(data, dict) else {"raw": data})
        except Exception as e:
            return ProvisionResult(False, None, {}, error=str(e))

    async def check_mailbox_available(self, email: str) -> Optional[bool]:
        # Mailcow availability endpoint behavior varies by deployment; use DB uniqueness as primary.
        return None

    @staticmethod
    def _json_or_text(resp: httpx.Response) -> Any:
        try:
            return resp.json()
        except Exception:
            return {"text": resp.text}


class HostedEmailProviderService:
    def __init__(self):
        self.provider_name = (settings.HOSTED_EMAIL_PROVIDER or "mock").strip().lower()
        self.domain = (settings.HOSTED_EMAIL_DOMAIN or "").strip().lower()

    def is_enabled(self) -> bool:
        return bool(settings.HOSTED_EMAIL_ENABLED and self.domain)

    def build_email_address(self, local_part: str) -> str:
        lp = (local_part or "").strip().lower()
        return f"{lp}@{self.domain}"

    def validate_local_part(self, local_part: str) -> Tuple[bool, str]:
        lp = (local_part or "").strip().lower()
        if not lp:
            return False, "Local part is required"
        if not LOCAL_PART_REGEX.match(lp):
            return False, "Invalid local part format"
        return True, ""

    def generate_mailbox_password(self) -> str:
        length = max(16, int(settings.HOSTED_EMAIL_DEFAULT_PASSWORD_LENGTH or 24))
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    async def check_address_available(self, email: str, session: AsyncSession) -> bool:
        result = await session.execute(select(UserEmailAccount.id).where(UserEmailAccount.email == email))
        return result.scalar_one_or_none() is None

    async def provision_mailbox_for_user(
        self,
        session: AsyncSession,
        user_id: str,
        local_part: str,
        display_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.is_enabled():
            raise ValueError("Hosted email is disabled or HOSTED_EMAIL_DOMAIN is not configured")

        valid, error = self.validate_local_part(local_part)
        if not valid:
            raise ValueError(error)

        email = self.build_email_address(local_part)
        available = await self.check_address_available(email, session)
        if not available:
            raise ValueError("Requested email is already taken")

        mailbox_password = self.generate_mailbox_password()
        provisioning = HostedMailboxProvisioning(
            user_id=user_id,
            email=email,
            provider=self.provider_name,
            status="requested",
            response_payload={},
        )
        session.add(provisioning)
        await session.flush()

        client = self._build_client()
        result = await client.provision_mailbox(
            email=email,
            password=mailbox_password,
            display_name=display_name,
            quota_mb=int(settings.HOSTED_EMAIL_MAILBOX_QUOTA_MB or 1024),
        )

        if not result.success:
            provisioning.status = "failed"
            provisioning.error_message = result.error
            provisioning.response_payload = result.response_payload or {}
            await session.flush()
            raise ValueError(result.error or "Failed to provision mailbox")

        account = await self._create_or_update_hosted_account(
            session=session,
            user_id=user_id,
            email=email,
            mailbox_password=mailbox_password,
            display_name=display_name,
        )

        provisioning.status = "provisioned"
        provisioning.account_id = account.id
        provisioning.external_reference = result.external_reference
        provisioning.response_payload = result.response_payload or {}
        await session.flush()

        return {
            "account": account,
            "mailbox_password": mailbox_password,
            "provisioning": provisioning,
        }

    async def _create_or_update_hosted_account(
        self,
        session: AsyncSession,
        user_id: str,
        email: str,
        mailbox_password: str,
        display_name: Optional[str],
    ) -> UserEmailAccount:
        result = await session.execute(
            select(UserEmailAccount).where(
                and_(
                    UserEmailAccount.user_id == user_id,
                    UserEmailAccount.email == email,
                )
            )
        )
        account = result.scalar_one_or_none()

        imap_host = settings.HOSTED_EMAIL_IMAP_HOST or settings.SMTP_HOST or ""
        smtp_host = settings.HOSTED_EMAIL_SMTP_HOST or settings.SMTP_HOST or ""
        if not imap_host or not smtp_host:
            raise ValueError("Hosted email IMAP/SMTP hosts are not configured")

        if account:
            account.provider = "hosted_internal"
            account.email_account_type = "hosted_internal"
            account.hosted_provider = self.provider_name
            account.display_name = display_name or account.display_name or email
            account.imap_host = imap_host
            account.imap_port = int(settings.HOSTED_EMAIL_IMAP_PORT)
            account.smtp_host = smtp_host
            account.smtp_port = int(settings.HOSTED_EMAIL_SMTP_PORT)
            account.use_tls = bool(settings.HOSTED_EMAIL_USE_TLS)
            account.encrypted_password = encrypt_credential(mailbox_password)
            account.is_active = True
            account.sync_enabled = True
            account.send_limit_daily = int(settings.HOSTED_EMAIL_DAILY_SEND_LIMIT or 0)
            await session.flush()
            return account

        account = UserEmailAccount(
            user_id=user_id,
            provider="hosted_internal",
            email_account_type="hosted_internal",
            hosted_provider=self.provider_name,
            email=email,
            display_name=display_name or email,
            imap_host=imap_host,
            imap_port=int(settings.HOSTED_EMAIL_IMAP_PORT),
            smtp_host=smtp_host,
            smtp_port=int(settings.HOSTED_EMAIL_SMTP_PORT),
            use_tls=bool(settings.HOSTED_EMAIL_USE_TLS),
            encrypted_password=encrypt_credential(mailbox_password),
            is_primary=False,
            is_active=True,
            sync_enabled=True,
            send_limit_daily=int(settings.HOSTED_EMAIL_DAILY_SEND_LIMIT or 0),
        )
        session.add(account)
        await session.flush()
        return account

    def _build_client(self) -> BaseHostedProviderClient:
        provider = self.provider_name
        if provider == "mock":
            return MockHostedProviderClient()

        base_url = settings.get_hosted_provider_api_base()
        api_key = settings.get_hosted_provider_api_key()
        if not base_url or not api_key:
            logger.warning(
                "Hosted provider %s selected but API credentials are missing. Falling back to mock provider.",
                provider,
            )
            return MockHostedProviderClient()

        if provider == "mailcow":
            return MailcowHostedProviderClient(base_url=base_url, api_key=api_key)

        # Non-mailcow providers can be added with dedicated clients.
        logger.warning("Hosted provider '%s' is not implemented. Falling back to mock.", provider)
        return MockHostedProviderClient()

