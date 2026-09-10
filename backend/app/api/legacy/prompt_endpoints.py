"""Prompt endpoints."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import PromptCreateRequest, PromptUpdateRequest
from app.core.logging import get_logger
from app.core.security import get_current_user
from app.models.database import get_db
from app.models.user_models import User
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService

router = APIRouter()
# Preserve the established log category for compatibility with operational filters.
logger = get_logger("app.api.endpoints")


@router.get("/prompts/my", response_model=List[Dict[str, Any]])
async def get_user_prompts(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get user's prompts"""
    try:
        prompt_service = PromptService(db)
        return await prompt_service.get_all_prompts()
    except Exception as e:
        logger.error(f"Error getting user prompts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get prompts")


@router.post("/prompts/{prompt_id}/test")
async def test_prompt(
    prompt_id: str, test_data: dict, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Test a prompt with sample input"""
    try:
        from sqlalchemy import select

        from app.models.prompt_models import PromptTemplate

        prompt_service = PromptService(db)
        llm_service = LLMService()

        # Get the prompt
        result = await db.execute(select(PromptTemplate).where(PromptTemplate.id == prompt_id))
        prompt = result.scalar_one_or_none()

        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt not found")

        # Get test input
        email_content = test_data.get("email_content", "")

        # Process the prompt with the test input
        result = await llm_service.process_prompt(prompt.template, email_content)

        return {
            "prompt_id": prompt_id,
            "prompt_name": prompt.name,
            "input": email_content,
            "output": result,
            "success": True,
        }

    except Exception as e:
        logger.error(f"Error testing prompt: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test prompt: {str(e)}")


@router.get("/system-prompts")
async def get_system_prompts(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get all system prompts"""
    try:
        prompt_service = PromptService(db)
        system_prompts = await prompt_service.get_all_system_prompts()
        return system_prompts
    except Exception as e:
        logger.error(f"Error getting system prompts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system prompts")


@router.get("/prompts", response_model=List[Dict[str, Any]])
async def get_prompts(db: AsyncSession = Depends(get_db)):
    """Get all prompts (public for demo)"""
    prompt_service = PromptService(db)
    return await prompt_service.get_all_prompts()


@router.post("/prompts", response_model=Dict[str, Any])
async def create_prompt(prompt_data: PromptCreateRequest, db: AsyncSession = Depends(get_db)):
    """Create a new prompt"""
    prompt_service = PromptService(db)
    return await prompt_service.create_prompt(prompt_data.model_dump())


@router.put("/prompts/{prompt_id}", response_model=Dict[str, Any])
async def update_prompt(prompt_id: str, prompt_data: PromptUpdateRequest, db: AsyncSession = Depends(get_db)):
    """Update a prompt"""
    prompt_service = PromptService(db)
    updated = await prompt_service.update_prompt(prompt_id, prompt_data.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return updated


@router.delete("/prompts/{prompt_id}")
async def delete_prompt(prompt_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a prompt"""
    prompt_service = PromptService(db)
    success = await prompt_service.delete_prompt(prompt_id)
    if not success:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"message": "Prompt deleted successfully"}
