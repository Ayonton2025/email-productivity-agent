"""Gmail provider adapter."""

from typing import Any, Dict

from .base import EmailProviderAdapter


class GmailProviderAdapter(EmailProviderAdapter):
    async def send(self, transport: Any, payload: Dict[str, Any]) -> bool:
        return await transport._send_gmail_reply(str(payload.get("original_email_id", "")), payload)
