"""
Email simulator endpoints for onboarding/training.
"""

from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import get_current_user
from app.models.user_models import User

router = APIRouter(prefix="/simulator", tags=["simulator"])


class SimulatorRequest(BaseModel):
    scenario: str = "support"
    difficulty: str = "medium"
    count: int = 5


@router.post("/generate-inbox", response_model=Dict[str, Any])
async def generate_simulated_inbox(
    body: SimulatorRequest,
    current_user: User = Depends(get_current_user),
):
    emails: List[Dict[str, Any]] = []
    for i in range(max(1, min(20, body.count))):
        emails.append(
            {
                "id": f"sim-{i+1}",
                "sender": f"{body.scenario}{i+1}@example.com",
                "subject": f"[{body.difficulty}] Training email {i+1}",
                "body": "Please draft a response with clear action items and polite tone.",
            }
        )
    return {"success": True, "user_id": current_user.id, "emails": emails}
