"""Canonical user model, shared by authentication, billing and email services."""

import logging
import uuid
from datetime import datetime, timedelta

import jwt
from sqlalchemy import Boolean, Column, DateTime, String

from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.models.base import Base
from app.models.email_models import UserEmailAccount

__all__ = ["Base", "User", "UserEmailAccount"]
logger = logging.getLogger(__name__)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    verification_token = Column(String, nullable=True)
    reset_token = Column(String, nullable=True)
    plan = Column(String, default="personal", index=True)
    subscription_status = Column(String, default="free", index=True)
    preferred_language = Column(String, default="en", index=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password: str):
        """Hash and set password with bcrypt length validation"""
        # Validate password length for bcrypt (72 character limit)
        if len(password) > 72:
            raise ValueError("Password cannot be longer than 72 characters")

        self.password_hash = get_password_hash(password)
        logger.info(f"🔑 [User] Password hashed successfully for: {self.email}")

    def check_password(self, password: str) -> bool:
        """Check password against hash"""
        try:
            result = verify_password(password, self.password_hash)
            logger.info(f"🔑 [User] Password check for {self.email}: {result}")
            return result
        except Exception as e:
            logger.error(f"❌ [User] Password verification failed: {e}")
            return False

    def generate_verification_token(self) -> str:
        """Generate email verification token"""
        if self.id is None:
            self.id = str(uuid.uuid4())
        token_data = {"user_id": self.id, "email": self.email, "exp": datetime.utcnow() + timedelta(days=1)}
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")
        self.verification_token = token
        logger.info("User verification token generated", extra={"user_id": str(self.id)})
        return token

    def generate_reset_token(self) -> str:
        """Generate password reset token"""
        if self.id is None:
            self.id = str(uuid.uuid4())
        token_data = {"user_id": self.id, "email": self.email, "exp": datetime.utcnow() + timedelta(hours=1)}
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")
        self.reset_token = token
        return token

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "plan": self.plan,
            "subscription_status": self.subscription_status,
            "preferred_language": self.preferred_language,
            "is_verified": self.is_verified,
            "is_active": self.is_active,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat(),
        }
