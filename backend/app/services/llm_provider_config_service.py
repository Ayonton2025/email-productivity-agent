from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_credential, encrypt_credential
from app.models.llm_provider_models import LLMProviderConfig

logger = logging.getLogger("email_productivity_agent.llm_provider_config")


@dataclass
class RuntimeProviderConfig:
    provider: str
    display_name: str
    model: str
    endpoint: Optional[str]
    api_keys: List[str]
    additional_headers: Dict[str, str]
    extra_config: Dict[str, Any]
    max_retries: int
    backoff_seconds: float
    timeout_seconds: int
    priority: int


class LLMProviderConfigService:
    PROVIDER_CATALOG: Dict[str, Dict[str, Any]] = {
        "groq": {"display_name": "Groq", "default_model": "llama-3.3-70b-versatile", "default_endpoint": "https://api.groq.com/openai/v1"},
        "google": {"display_name": "Google Gemini", "default_model": "gemini-1.5-flash", "default_endpoint": None},
        "openrouter": {"display_name": "OpenRouter", "default_model": "deepseek/deepseek-chat-v3-0324:free", "default_endpoint": "https://openrouter.ai/api/v1"},
        "huggingface": {"display_name": "Hugging Face", "default_model": "mistralai/Mistral-7B-Instruct-v0.3", "default_endpoint": "https://api-inference.huggingface.co/models"},
        "ollama": {"display_name": "Ollama", "default_model": "llama3.1", "default_endpoint": "http://localhost:11434"},
        "openai": {"display_name": "OpenAI", "default_model": "gpt-4o-mini", "default_endpoint": "https://api.openai.com/v1"},
        "anthropic": {"display_name": "Anthropic", "default_model": "claude-3-5-haiku-20241022", "default_endpoint": "https://api.anthropic.com"},
        "cloudflare": {"display_name": "Cloudflare Workers AI", "default_model": "@cf/meta/llama-3.1-8b-instruct", "default_endpoint": "https://api.cloudflare.com/client/v4"},
        "github_models": {"display_name": "GitHub Models", "default_model": "gpt-4o-mini", "default_endpoint": "https://models.inference.ai.azure.com"},
        "mistral": {"display_name": "Mistral", "default_model": "mistral-small-latest", "default_endpoint": "https://api.mistral.ai/v1"},
        "cohere": {"display_name": "Cohere", "default_model": "command-r", "default_endpoint": "https://api.cohere.com/v2"},
        "together": {"display_name": "Together AI", "default_model": "meta-llama/Llama-3.1-8B-Instruct-Turbo", "default_endpoint": "https://api.together.xyz/v1"},
        "cerebras": {"display_name": "Cerebras", "default_model": "llama3.1-8b", "default_endpoint": "https://api.cerebras.ai/v1"},
        "replicate": {"display_name": "Replicate", "default_model": "meta/llama-3-8b-instruct", "default_endpoint": "https://api.replicate.com/v1"},
        "nebius": {"display_name": "Nebius", "default_model": "meta-llama/Meta-Llama-3.1-8B-Instruct", "default_endpoint": "https://api.studio.nebius.ai/v1"},
        "alibaba": {"display_name": "Alibaba Model Studio", "default_model": "qwen-plus", "default_endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
        "fireworks": {"display_name": "Fireworks AI", "default_model": "accounts/fireworks/models/llama-v3p1-8b-instruct", "default_endpoint": "https://api.fireworks.ai/inference/v1"},
        "nvidia_nim": {"display_name": "NVIDIA NIM", "default_model": "meta/llama-3.1-8b-instruct", "default_endpoint": "https://integrate.api.nvidia.com/v1"},
    }

    @classmethod
    async def ensure_catalog_rows(cls, session: AsyncSession) -> None:
        existing = await session.execute(select(LLMProviderConfig))
        by_provider = {row.provider: row for row in existing.scalars().all()}

        for idx, (provider, info) in enumerate(cls.PROVIDER_CATALOG.items(), start=1):
            if provider in by_provider:
                continue
            session.add(
                LLMProviderConfig(
                    provider=provider,
                    display_name=info["display_name"],
                    is_enabled=False,
                    priority=idx * 10,
                    model=info["default_model"],
                    endpoint=info.get("default_endpoint"),
                    api_keys_encrypted=[],
                    additional_headers={},
                    extra_config={},
                )
            )
        await session.flush()

    @classmethod
    async def list_configs(cls, session: AsyncSession) -> List[LLMProviderConfig]:
        await cls.ensure_catalog_rows(session)
        result = await session.execute(
            select(LLMProviderConfig).order_by(LLMProviderConfig.priority.asc(), LLMProviderConfig.provider.asc())
        )
        return list(result.scalars().all())

    @classmethod
    async def get_config(cls, session: AsyncSession, provider: str) -> Optional[LLMProviderConfig]:
        await cls.ensure_catalog_rows(session)
        result = await session.execute(
            select(LLMProviderConfig).where(LLMProviderConfig.provider == provider.strip().lower())
        )
        return result.scalar_one_or_none()

    @classmethod
    def _decrypt_keys(cls, encrypted_keys: Any) -> List[str]:
        out: List[str] = []
        if not isinstance(encrypted_keys, list):
            return out
        for item in encrypted_keys:
            if not item or not isinstance(item, str):
                continue
            try:
                out.append(decrypt_credential(item))
            except Exception:
                # Log a warning so admins can detect decryption issues (no key material printed)
                logger.warning("Failed to decrypt one API key entry (possibly wrong ENCRYPTION_KEY or corrupted data)")
                continue
        return out

    @classmethod
    def _encrypt_keys(cls, keys: List[str]) -> List[str]:
        encrypted: List[str] = []
        for key in keys:
            value = (key or "").strip()
            if not value:
                continue
            encrypted.append(encrypt_credential(value))
        return encrypted

    @classmethod
    def _mask_key(cls, key: str) -> str:
        cleaned = (key or "").strip()
        if len(cleaned) <= 8:
            return "*" * len(cleaned)
        return f"{cleaned[:4]}{'*' * (len(cleaned) - 8)}{cleaned[-4:]}"

    @classmethod
    def to_admin_payload(cls, row: LLMProviderConfig) -> Dict[str, Any]:
        keys = cls._decrypt_keys(row.api_keys_encrypted)
        encrypted_count = len(row.api_keys_encrypted or [])
        decrypted_count = len(keys)
        decryption_failures = max(0, encrypted_count - decrypted_count)
        return {
            "provider": row.provider,
            "display_name": row.display_name,
            "is_enabled": bool(row.is_enabled),
            "priority": int(row.priority or 100),
            "model": row.model,
            "endpoint": row.endpoint,
            "key_count": decrypted_count,
            "encrypted_key_count": encrypted_count,
            "decryption_failures": decryption_failures,
            "masked_keys": [cls._mask_key(k) for k in keys],
            "has_keys": decrypted_count > 0,
            "additional_headers": row.additional_headers or {},
            "extra_config": row.extra_config or {},
            "max_retries": int(row.max_retries or 2),
            "backoff_seconds": float(row.backoff_seconds or 0.8),
            "timeout_seconds": int(row.timeout_seconds or 30),
            "is_healthy": bool(row.is_healthy),
            "last_error": row.last_error,
            "last_checked_at": row.last_checked_at.isoformat() if row.last_checked_at else None,
            "updated_by": row.updated_by,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    @classmethod
    async def upsert_config(
        cls,
        session: AsyncSession,
        provider: str,
        *,
        updated_by: Optional[str],
        payload: Dict[str, Any],
    ) -> LLMProviderConfig:
        provider_key = provider.strip().lower()
        row = await cls.get_config(session, provider_key)
        if row is None:
            info = cls.PROVIDER_CATALOG.get(provider_key, {})
            row = LLMProviderConfig(
                provider=provider_key,
                display_name=info.get("display_name", provider_key.replace("_", " ").title()),
                model=info.get("default_model"),
                endpoint=info.get("default_endpoint"),
            )
            session.add(row)

        if "display_name" in payload:
            row.display_name = payload["display_name"] or row.display_name
        if "is_enabled" in payload:
            row.is_enabled = bool(payload["is_enabled"])
        if "priority" in payload and payload["priority"] is not None:
            row.priority = int(payload["priority"])
        if "model" in payload:
            row.model = payload["model"] or None
        if "endpoint" in payload:
            row.endpoint = payload["endpoint"] or None
        if "additional_headers" in payload and isinstance(payload["additional_headers"], dict):
            row.additional_headers = payload["additional_headers"]
        if "extra_config" in payload and isinstance(payload["extra_config"], dict):
            row.extra_config = payload["extra_config"]
        if "max_retries" in payload and payload["max_retries"] is not None:
            row.max_retries = max(1, int(payload["max_retries"]))
        if "backoff_seconds" in payload and payload["backoff_seconds"] is not None:
            row.backoff_seconds = max(0.0, float(payload["backoff_seconds"]))
        if "timeout_seconds" in payload and payload["timeout_seconds"] is not None:
            row.timeout_seconds = max(5, int(payload["timeout_seconds"]))
        if "api_keys" in payload and isinstance(payload["api_keys"], list):
            row.api_keys_encrypted = cls._encrypt_keys(payload["api_keys"])

        row.updated_by = updated_by
        row.updated_at = datetime.utcnow()
        await session.flush()
        return row

    @classmethod
    async def rotate_key(
        cls,
        session: AsyncSession,
        provider: str,
        *,
        updated_by: Optional[str],
        new_key: str,
    ) -> LLMProviderConfig:
        row = await cls.get_config(session, provider)
        if row is None:
            row = await cls.upsert_config(session, provider, updated_by=updated_by, payload={})
        keys = cls._decrypt_keys(row.api_keys_encrypted)
        value = (new_key or "").strip()
        if value:
            keys.insert(0, value)
        row.api_keys_encrypted = cls._encrypt_keys(keys)
        row.updated_by = updated_by
        row.updated_at = datetime.utcnow()
        await session.flush()
        return row

    @classmethod
    async def delete_key(
        cls,
        session: AsyncSession,
        provider: str,
        *,
        updated_by: Optional[str],
        key_index: int,
    ) -> LLMProviderConfig:
        row = await cls.get_config(session, provider)
        if row is None:
            raise ValueError(f"Provider '{provider}' not configured")
        keys = cls._decrypt_keys(row.api_keys_encrypted)
        if 0 <= key_index < len(keys):
            keys.pop(key_index)
        row.api_keys_encrypted = cls._encrypt_keys(keys)
        row.updated_by = updated_by
        row.updated_at = datetime.utcnow()
        await session.flush()
        return row

    @classmethod
    async def get_runtime_configs(cls, session: AsyncSession, include_disabled: bool = False) -> List[RuntimeProviderConfig]:
        rows = await cls.list_configs(session)
        out: List[RuntimeProviderConfig] = []
        for row in rows:
            if not row.is_enabled and not include_disabled:
                continue
            keys = cls._decrypt_keys(row.api_keys_encrypted)
            out.append(
                RuntimeProviderConfig(
                    provider=row.provider,
                    display_name=row.display_name,
                    model=row.model or cls.PROVIDER_CATALOG.get(row.provider, {}).get("default_model", ""),
                    endpoint=row.endpoint,
                    api_keys=keys,
                    additional_headers=row.additional_headers or {},
                    extra_config=row.extra_config or {},
                    max_retries=max(1, int(row.max_retries or 1)),
                    backoff_seconds=max(0.0, float(row.backoff_seconds or 0.0)),
                    timeout_seconds=max(5, int(row.timeout_seconds or 30)),
                    priority=int(row.priority or 100),
                )
            )
        return out

    @classmethod
    async def update_health(
        cls,
        session: AsyncSession,
        provider: str,
        *,
        healthy: bool,
        error: Optional[str],
    ) -> None:
        row = await cls.get_config(session, provider)
        if not row:
            return
        row.is_healthy = bool(healthy)
        row.last_error = error[:2000] if error else None
        row.last_checked_at = datetime.utcnow()
        await session.flush()
