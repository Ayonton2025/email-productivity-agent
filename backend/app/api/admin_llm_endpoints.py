from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_current_user
from app.models.database import User, get_db
from app.services.llm_orchestration_service import llm_service
from app.services.llm_provider_config_service import LLMProviderConfigService


router = APIRouter(prefix="/api/v1/admin/llm", tags=["admin-llm"])


def _is_super_admin(user: User) -> bool:
    allowed = {e.strip().lower() for e in (settings.ADMIN_EMAILS or "").split(",") if e.strip()}
    return bool(user.email and user.email.lower() in allowed)


class ProviderUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    is_enabled: Optional[bool] = None
    priority: Optional[int] = None
    model: Optional[str] = None
    endpoint: Optional[str] = None
    api_keys: Optional[List[str]] = Field(default=None, description="Provide to replace full key pool")
    additional_headers: Optional[Dict[str, str]] = None
    extra_config: Optional[Dict[str, Any]] = None
    max_retries: Optional[int] = None
    backoff_seconds: Optional[float] = None
    timeout_seconds: Optional[int] = None


class RotateKeyRequest(BaseModel):
    api_key: str


class DeleteKeyRequest(BaseModel):
    key_index: int = Field(description="Index of the key to delete (0-based)")


class RotateAllKeysRequest(BaseModel):
    new_encryption_key: str
    old_encryption_key: Optional[str] = None
    provider: Optional[str] = None
    dry_run: Optional[bool] = False


@router.get("/providers")
async def list_provider_configs(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    rows = await LLMProviderConfigService.list_configs(session)
    return {
        "success": True,
        "providers": [LLMProviderConfigService.to_admin_payload(row) for row in rows],
        "catalog": LLMProviderConfigService.PROVIDER_CATALOG,
    }


@router.put("/providers/{provider}")
async def upsert_provider_config(
    provider: str,
    request: ProviderUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    row = await LLMProviderConfigService.upsert_config(
        session,
        provider=provider,
        updated_by=current_user.id,
        payload=request.dict(exclude_unset=True),
    )
    return {"success": True, "provider": LLMProviderConfigService.to_admin_payload(row)}


@router.post("/providers/{provider}/keys/rotate")
async def rotate_provider_key(
    provider: str,
    request: RotateKeyRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if not request.api_key.strip():
        raise HTTPException(status_code=400, detail="api_key is required")
    row = await LLMProviderConfigService.rotate_key(
        session,
        provider=provider,
        updated_by=current_user.id,
        new_key=request.api_key.strip(),
    )
    return {"success": True, "provider": LLMProviderConfigService.to_admin_payload(row)}


@router.post("/providers/{provider}/keys/delete")
async def delete_provider_key(
    provider: str,
    request: DeleteKeyRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if not isinstance(request.key_index, int) or request.key_index < 0:
        raise HTTPException(status_code=400, detail="key_index must be a non-negative integer")
    row = await LLMProviderConfigService.delete_key(
        session,
        provider=provider,
        updated_by=current_user.id,
        key_index=request.key_index,
    )
    return {"success": True, "provider": LLMProviderConfigService.to_admin_payload(row)}


@router.post("/providers/health-check")
async def live_health_check(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    health = await llm_service.provider_health(session=session, include_live_checks=True)
    for item in health.get("providers", []):
        await LLMProviderConfigService.update_health(
            session,
            provider=item.get("provider", ""),
            healthy=item.get("status") == "healthy",
            error=item.get("reason"),
        )
    rows = await LLMProviderConfigService.list_configs(session)
    return {
        "success": True,
        "health": health,
        "providers": [LLMProviderConfigService.to_admin_payload(row) for row in rows],
    }


@router.post("/providers/live-test")
async def live_providers_test(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Run live sample prompts against each enabled provider (admin-only)."""
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    # Run tests
    test_results = await llm_service.test_providers(session=session)

    # Update provider health rows based on tests
    for res in test_results.get("results", []):
        provider = res.get("provider")
        healthy = bool(res.get("success"))
        reason = None if healthy else res.get("error")
        await LLMProviderConfigService.update_health(session, provider=provider, healthy=healthy, error=reason)

    rows = await LLMProviderConfigService.list_configs(session)
    return {
        "success": True,
        "test_results": test_results,
        "providers": [LLMProviderConfigService.to_admin_payload(row) for row in rows],
    }


@router.post("/providers/{provider}/health-check")
async def live_single_provider_health_check(
    provider: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Run live health check for one provider (admin-only)."""
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    provider_key = (provider or "").strip().lower()
    if not provider_key:
        raise HTTPException(status_code=400, detail="provider is required")

    health = await llm_service.provider_health(
        session=session,
        include_live_checks=True,
        provider=provider_key,
    )
    for item in health.get("providers", []):
        await LLMProviderConfigService.update_health(
            session,
            provider=item.get("provider", ""),
            healthy=item.get("status") == "healthy",
            error=item.get("reason"),
        )
    rows = await LLMProviderConfigService.list_configs(session)
    provider_health = next((p for p in health.get("providers", []) if p.get("provider") == provider_key), None)
    return {
        "success": True,
        "provider_health": provider_health,
        "health": health,
        "providers": [LLMProviderConfigService.to_admin_payload(row) for row in rows],
    }


@router.post("/providers/{provider}/live-test")
async def live_single_provider_test(
    provider: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Run live sample prompt test against one provider (admin-only)."""
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    provider_key = (provider or "").strip().lower()
    if not provider_key:
        raise HTTPException(status_code=400, detail="provider is required")

    test_results = await llm_service.test_providers(session=session, provider=provider_key)
    for res in test_results.get("results", []):
        tested_provider = res.get("provider")
        healthy = bool(res.get("success"))
        reason = None if healthy else res.get("error")
        await LLMProviderConfigService.update_health(session, provider=tested_provider, healthy=healthy, error=reason)

    rows = await LLMProviderConfigService.list_configs(session)
    provider_result = next((r for r in test_results.get("results", []) if r.get("provider") == provider_key), None)
    return {
        "success": True,
        "provider_result": provider_result,
        "test_results": test_results,
        "providers": [LLMProviderConfigService.to_admin_payload(row) for row in rows],
    }


@router.get("/providers/diagnostic")
async def providers_diagnostic(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Return diagnostic info about provider key decryption and counts (admin-only)."""
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    rows = await LLMProviderConfigService.list_configs(session)
    out = []
    for r in rows:
        payload = LLMProviderConfigService.to_admin_payload(r)
        out.append({
            "provider": r.provider,
            "display_name": r.display_name,
            "encrypted_key_count": payload.get("encrypted_key_count", 0),
            "decrypted_key_count": payload.get("key_count", 0),
            "decryption_failures": payload.get("decryption_failures", 0),
            "is_enabled": bool(r.is_enabled),
            "is_healthy": bool(r.is_healthy),
            "last_error": r.last_error,
        })

    return {"success": True, "diagnostic": out}



@router.post("/providers/keys/rotate-all")
async def rotate_all_provider_keys(
    request: RotateAllKeysRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Admin-only endpoint to rotate/re-encrypt provider API key pools.

    This temporarily uses the provided `old_encryption_key` (if any) to decrypt
    existing DB values and then re-encrypts them with `new_encryption_key`.
    Use `dry_run=true` to preview changes without committing.
    """
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    new_key = (request.new_encryption_key or "").strip()
    if not new_key:
        raise HTTPException(status_code=400, detail="new_encryption_key is required")

    provider_filter = (request.provider or "").strip().lower() if request.provider else None
    dry_run = bool(request.dry_run)

    original_key = settings.ENCRYPTION_KEY

    # If provided, use old key for decryption phase
    if request.old_encryption_key:
        settings.ENCRYPTION_KEY = request.old_encryption_key

    rows = await LLMProviderConfigService.list_configs(session)
    results = []
    changed = []

    for row in rows:
        if provider_filter and row.provider != provider_filter:
            continue

        encrypted_count = len(row.api_keys_encrypted or [])
        decrypted_keys = LLMProviderConfigService._decrypt_keys(row.api_keys_encrypted or [])
        decryption_failures = max(0, encrypted_count - len(decrypted_keys))

        entry = {
            "provider": row.provider,
            "encrypted_count": encrypted_count,
            "decrypted_ok": len(decrypted_keys),
            "decryption_failures": decryption_failures,
            "changed": False,
        }

        if not decrypted_keys:
            entry["reason"] = "no decrypted keys available"
            results.append(entry)
            continue

        # Switch to new key and re-encrypt
        settings.ENCRYPTION_KEY = new_key
        re_encrypted = LLMProviderConfigService._encrypt_keys(decrypted_keys)

        if re_encrypted == (row.api_keys_encrypted or []):
            entry["reason"] = "already encrypted with target key"
            results.append(entry)
        else:
            entry["would_replace_count"] = len(row.api_keys_encrypted or [])
            if dry_run:
                entry["changed"] = False
                results.append(entry)
            else:
                row.api_keys_encrypted = re_encrypted
                await session.flush()
                entry["changed"] = True
                changed.append(row.provider)
                results.append(entry)

        # restore decryption key for next provider
        if request.old_encryption_key:
            settings.ENCRYPTION_KEY = request.old_encryption_key
        else:
            settings.ENCRYPTION_KEY = original_key

    if changed and not dry_run:
        await session.commit()

    # Restore original runtime key
    settings.ENCRYPTION_KEY = original_key

    return {"success": True, "results": results, "changed": changed}
