"""Signed confirmation bound to the user and previewed draft."""

import base64
import hashlib
import hmac
import json
import time

from fastapi import HTTPException

from app.core.config import settings


def _canonical_draft_hash(page: str, objective: str, draft: dict) -> str:
    canonical = json.dumps(
        {"page": (page or "").strip().lower(), "objective": (objective or "").strip(), "draft": draft or {}},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _create_confirmation_token(user_id: str, page: str, objective: str, draft: dict) -> str:
    exp = int(time.time()) + 600  # 10 minutes
    payload = {
        "uid": user_id,
        "exp": exp,
        "digest": _canonical_draft_hash(page, objective, draft),
    }
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=True)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8")
    signature = hmac.new(settings.SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"


def _decode_confirmation_token(token: str) -> dict:
    try:
        payload_b64, signature = token.split(".", 1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid confirmation token format")

    expected = hmac.new(settings.SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=400, detail="Invalid confirmation token signature")

    try:
        payload_json = base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8")
        payload = json.loads(payload_json)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid confirmation token payload")
    return payload


def _validate_confirmation_token(token_payload: dict, user_id: str, page: str, objective: str, draft: dict) -> None:
    if token_payload.get("uid") != user_id:
        raise HTTPException(status_code=403, detail="Token user mismatch")
    if int(token_payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(status_code=400, detail="Confirmation token expired")
    expected_digest = _canonical_draft_hash(page, objective, draft)
    if token_payload.get("digest") != expected_digest:
        raise HTTPException(status_code=400, detail="Draft changed since preview; regenerate and confirm again")
