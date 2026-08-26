# Export models for easy importing
from app.models.database import (
    Base,
    Email,
    User,
    UserEmailAccount,
    # core DB utilities can be added here
)
from app.models.document_models import (
    DocumentAnalysis,
    EmailAttachment,
)

__all__ = [
    # Database models
    "Base",
    "User",
    "Email",
    "UserEmailAccount",
    # Document models
    "EmailAttachment",
    "DocumentAnalysis",
]
