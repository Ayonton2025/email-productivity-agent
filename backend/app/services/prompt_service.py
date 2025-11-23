import json
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.database import PromptTemplate

class PromptService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def initialize_default_prompts(self):
        """Initialize default prompt templates"""
        default_prompts = [
            {
                "name": "Default Categorization",
                "description": "Categorize emails into Important, Newsletter, Spam, or To-Do",
                "template": "Categorize this email into one of: Important, Newsletter, Spam, To-Do. Important emails are from key contacts or contain urgent matters. Newsletter are mass distributions. Spam is unsolicited commercial email. To-Do emails require specific action from the recipient. Respond with only the category name.",
                "category": "categorization"
            },
            {
                "name": "Action Item Extraction",
                "description": "Extract tasks and deadlines from emails",
                "template": "Extract actionable tasks from this email. Respond in JSON format: { \"tasks\": [ { \"task\": \"description\", \"deadline\": \"date or null\", \"priority\": \"high/medium/low\" } ] }. If no clear tasks, return empty array.",
                "category": "action_extraction"
            },
            {
                "name": "Smart Summary",
                "description": "Create concise email summaries",
                "template": "Summarize this email in 2-3 sentences. Focus on key points, requests, and required actions. Be concise but informative.",
                "category": "summary"
            },
            {
                "name": "Professional Reply",
                "description": "Draft professional email responses",
                "template": "Draft a professional email reply. Be polite, address all points in the original email, and maintain a professional tone. If it's a meeting request, ask for an agenda. If it's a task request, acknowledge receipt and provide a tentative timeline.",
                "category": "reply_draft"
            }
        ]
        
        for prompt_data in default_prompts:
            # Check if prompt already exists
            result = await self.db.execute(
                select(PromptTemplate).where(PromptTemplate.name == prompt_data["name"])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                # CHANGED: Use prompt_metadata instead of metadata
                prompt_data["prompt_metadata"] = prompt_data.get("metadata", {})
                if "metadata" in prompt_data:
                    del prompt_data["metadata"]
                    
                prompt = PromptTemplate(**prompt_data)
                self.db.add(prompt)
        
        await self.db.commit()
    
    async def get_all_prompts(self) -> List[Dict[str, Any]]:
        """Get all prompt templates"""
        result = await self.db.execute(select(PromptTemplate).order_by(PromptTemplate.category, PromptTemplate.name))
        prompts = result.scalars().all()
        return [prompt.to_dict() for prompt in prompts]
    
    async def get_active_prompt(self, category: str) -> Optional[PromptTemplate]:
        """Get the active prompt for a category"""
        result = await self.db.execute(
            select(PromptTemplate).where(
                (PromptTemplate.category == category) & 
                (PromptTemplate.is_active == True)
            )
        )
        return result.scalar_one_or_none()
    
    async def create_prompt(self, prompt_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new prompt template"""
        # CHANGED: Handle metadata field conversion
        prompt_metadata = prompt_data.pop('metadata', {})
        prompt_data['prompt_metadata'] = prompt_metadata
        
        # Deactivate other prompts in the same category if this one is set to active
        if prompt_data.get('is_active', False):
            await self._deactivate_other_prompts(prompt_data['category'])
        
        prompt = PromptTemplate(**prompt_data)
        self.db.add(prompt)
        await self.db.commit()
        await self.db.refresh(prompt)
        return prompt.to_dict()
    
    async def update_prompt(self, prompt_id: str, prompt_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a prompt template"""
        result = await self.db.execute(select(PromptTemplate).where(PromptTemplate.id == prompt_id))
        prompt = result.scalar_one_or_none()
        
        if prompt:
            # CHANGED: Handle metadata field conversion
            if 'metadata' in prompt_data:
                prompt_data['prompt_metadata'] = prompt_data.pop('metadata')
            
            # Deactivate other prompts if this one is being activated
            if prompt_data.get('is_active', False) and not prompt.is_active:
                await self._deactivate_other_prompts(prompt.category, exclude_id=prompt_id)
            
            for key, value in prompt_data.items():
                setattr(prompt, key, value)
            
            prompt.version += 1
            await self.db.commit()
            await self.db.refresh(prompt)
            return prompt.to_dict()
        
        return None
    
    async def _deactivate_other_prompts(self, category: str, exclude_id: str = None):
        """Deactivate all prompts in a category except the excluded one"""
        query = select(PromptTemplate).where(
            (PromptTemplate.category == category) & 
            (PromptTemplate.is_active == True)
        )
        
        if exclude_id:
            query = query.where(PromptTemplate.id != exclude_id)
        
        result = await self.db.execute(query)
        prompts = result.scalars().all()
        
        for prompt in prompts:
            prompt.is_active = False
        
        await self.db.commit()