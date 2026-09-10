"""Compatibility entry point for the original API routes.

Domain modules own handler implementation. Preserve registration order, public
handler imports, and the service classes used by existing callers and tests.
"""

from fastapi import APIRouter

from app.api.legacy import (
    account_endpoints,
    agent_endpoints,
    draft_endpoints,
    email_endpoints,
    health_endpoints,
    inbox_endpoints,
    prompt_endpoints,
    reply_endpoints,
)
from app.api.legacy.account_endpoints import connect_gmail_simple, debug_email_accounts, get_user_email_accounts_simple
from app.api.legacy.agent_endpoints import chat_with_agent, get_agent_status, process_with_agent, websocket_agent
from app.api.legacy.draft_endpoints import create_draft, delete_draft, get_drafts, update_draft
from app.api.legacy.email_endpoints import (
    get_email,
    get_emails,
    load_mock_emails,
    load_mock_emails_if_empty,
    sync_user_emails,
    update_email_category,
)
from app.api.legacy.health_endpoints import api_info, health_ai, health_db
from app.api.legacy.inbox_endpoints import get_user_inbox
from app.api.legacy.prompt_endpoints import (
    create_prompt,
    delete_prompt,
    get_prompts,
    get_system_prompts,
    get_user_prompts,
    test_prompt,
    update_prompt,
)
from app.api.legacy.reply_endpoints import generate_email_reply
from app.services.email_service import EmailService
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService

__all__ = [
    "router",
    "EmailService",
    "LLMService",
    "PromptService",
    "get_user_inbox",
    "get_user_prompts",
    "test_prompt",
    "get_system_prompts",
    "sync_user_emails",
    "get_user_email_accounts_simple",
    "connect_gmail_simple",
    "debug_email_accounts",
    "get_emails",
    "load_mock_emails",
    "load_mock_emails_if_empty",
    "get_email",
    "update_email_category",
    "get_prompts",
    "create_prompt",
    "update_prompt",
    "delete_prompt",
    "get_drafts",
    "create_draft",
    "update_draft",
    "delete_draft",
    "generate_email_reply",
    "process_with_agent",
    "chat_with_agent",
    "get_agent_status",
    "websocket_agent",
    "health_db",
    "health_ai",
    "api_info",
]

_routes = []
for child in (
    inbox_endpoints,
    prompt_endpoints,
    account_endpoints,
    email_endpoints,
    draft_endpoints,
    reply_endpoints,
    agent_endpoints,
    health_endpoints,
):
    _routes.extend(child.router.routes)

# Static routes must retain their original precedence over parameter routes.
_ROUTE_ORDER = [
    "get_user_inbox",
    "get_user_prompts",
    "test_prompt",
    "get_system_prompts",
    "sync_user_emails",
    "get_user_email_accounts_simple",
    "connect_gmail_simple",
    "debug_email_accounts",
    "get_emails",
    "load_mock_emails",
    "load_mock_emails_if_empty",
    "get_email",
    "update_email_category",
    "get_prompts",
    "create_prompt",
    "update_prompt",
    "delete_prompt",
    "get_drafts",
    "create_draft",
    "update_draft",
    "delete_draft",
    "generate_email_reply",
    "process_with_agent",
    "chat_with_agent",
    "get_agent_status",
    "websocket_agent",
    "health_db",
    "health_ai",
    "api_info",
]
router = APIRouter(routes=sorted(_routes, key=lambda route: _ROUTE_ORDER.index(route.name)))
