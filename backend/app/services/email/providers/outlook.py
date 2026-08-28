"""Outlook provider adapter."""

from typing import Any, Dict

from .base import EmailProviderAdapter


class OutlookProviderAdapter(EmailProviderAdapter):
    async def send(self, transport: Any, payload: Dict[str, Any]) -> bool:
        return await transport._send_outlook_reply(
            str(payload.get("original_email_id", "")), payload
        )
