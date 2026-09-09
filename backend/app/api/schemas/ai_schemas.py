"""AI request and response contracts."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ClassifyEmailRequest(BaseModel):
    sender: str = Field(..., min_length=1, max_length=320)
    subject: str = Field(..., min_length=1, max_length=1000)
    body: str = Field(..., min_length=1, max_length=100000)


class ClassifyEmailResponse(BaseModel):
    category: str
    confidence: float
    reasoning: str


class ExtractActionsRequest(BaseModel):
    sender: str = Field(..., min_length=1, max_length=320)
    subject: str = Field(..., min_length=1, max_length=1000)
    body: str = Field(..., min_length=1, max_length=100000)


class ActionItem(BaseModel):
    task: str
    deadline: Optional[str] = None
    priority: str = "medium"
    assigned_to: Optional[str] = None


class ExtractActionsResponse(BaseModel):
    actions: List[ActionItem]


class AnalyzeSentimentRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=100000)


class AnalyzeSentimentResponse(BaseModel):
    sentiment: str  # positive, neutral, negative
    tone: str  # professional, casual, urgent, friendly
    confidence: float


class SummarizeThreadRequest(BaseModel):
    thread_content: str = Field(..., min_length=1, max_length=200000)


class AnalyzeRelationshipRequest(BaseModel):
    sender: str = Field(..., min_length=1, max_length=320)
    email_content: str = Field(..., min_length=1, max_length=100000)


class WorkspaceAssistRequest(BaseModel):
    page: str = Field(..., min_length=1, max_length=120)
    objective: str = Field(..., min_length=1, max_length=10000)
    mode: str = Field(default="draft", min_length=1, max_length=40)
    context: Optional[dict[str, object]] = None
    draft: Optional[dict[str, object]] = None
    confirmed: bool = False
    confirmation_token: Optional[str] = None


class RelationshipAnalysisResponse(BaseModel):
    relationship_score: float
    engagement_level: str
    relationship_type: str
