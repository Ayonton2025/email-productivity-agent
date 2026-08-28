"""Prompt templates owned independently from orchestration."""

from typing import Any, Dict, List


class PromptRegistry:
    PROMPTS = {
        "email_classifier": {
            "id": "email_classifier",
            "system_prompt": 'Return JSON {"category":"...","confidence":0.0,"reasoning":"..."}',
        },
        "action_extractor": {
            "id": "action_extractor",
            "system_prompt": 'Return JSON {"actions":[{"action":"...","deadline":"YYYY-MM-DD","priority":"High/Medium/Low","assigned_to":"name"}]}',
        },
        "sentiment_analyzer": {
            "id": "sentiment_analyzer",
            "system_prompt": 'Return JSON {"sentiment":"positive/neutral/negative","tone":"professional/casual/urgent/friendly","confidence":0.0}',
        },
        "email_summarizer": {
            "id": "email_summarizer",
            "system_prompt": 'Return JSON {"summary":"...","key_points":["..."]}',
        },
        "reply_generator": {
            "id": "reply_generator",
            "system_prompt": 'Return JSON {"reply":"...","tone":"professional/casual"}',
        },
        "relationship_scorer": {
            "id": "relationship_scorer",
            "system_prompt": 'Return JSON {"relationship_score":0.0,"relationship_type":"...","engagement_level":"..."}',
        },
    }

    @classmethod
    def get_prompt(cls, prompt_id: str) -> Dict[str, Any]:
        return cls.PROMPTS.get(prompt_id, {})

    @classmethod
    def list_prompts(cls) -> List[str]:
        return list(cls.PROMPTS.keys())
