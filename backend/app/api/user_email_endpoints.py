"""Compatibility aggregator for email-account API routes."""

from fastapi import APIRouter

from app.api.email_accounts.accounts import router as accounts_router
from app.api.email_accounts.connections import router as connections_router
from app.api.email_accounts.messages import router as messages_router
from app.api.email_accounts.oauth import router as oauth_router

router = APIRouter()
for child_router in (oauth_router, connections_router, accounts_router, messages_router):
    router.include_router(child_router)
