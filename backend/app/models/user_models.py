from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta
import uuid
import jwt
from app.core.config import settings
from app.core.security import get_password_hash, verify_password

Base = declarative_base()

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
    preferred_language = Column(String, default="en")
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password: str):
        """Hash and set password with bcrypt length validation"""
        # Validate password length for bcrypt (72 character limit)
        if len(password) > 72:
            raise ValueError("Password cannot be longer than 72 characters")
        
        self.password_hash = get_password_hash(password)
        print(f"🔑 [User] Password hashed successfully for: {self.email}")

    def check_password(self, password: str) -> bool:
        """Check password against hash"""
        try:
            result = verify_password(password, self.password_hash)
            print(f"🔑 [User] Password check for {self.email}: {result}")
            return result
        except Exception as e:
            print(f"❌ [User] Password verification failed: {e}")
            return False

    def generate_verification_token(self) -> str:
        """Generate email verification token"""
        token_data = {
            "user_id": self.id,
            "email": self.email,
            "exp": datetime.utcnow() + timedelta(days=1)
        }
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")
        self.verification_token = token
        print(f"🔐 [User] Verification token generated: {token[:20]}...")
        return token

    def generate_reset_token(self) -> str:
        """Generate password reset token"""
        token_data = {
            "user_id": self.id,
            "email": self.email,
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")
        self.reset_token = token
        return token

    def to_dict(self):
        """Convert user to dictionary"""
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "is_verified": self.is_verified,
            "is_active": self.is_active,
            "preferred_language": self.preferred_language,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat(),
        }

class UserEmailAccount(Base):
    __tablename__ = "user_email_accounts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    provider = Column(String, nullable=False)  # gmail, yahoo, outlook, etc
    email = Column(String, nullable=False, index=True)
    display_name = Column(String, nullable=True)
    
    # IMAP/SMTP Configuration
    imap_host = Column(String, nullable=False)
    imap_port = Column(Integer, default=993)
    smtp_host = Column(String, nullable=False)
    smtp_port = Column(Integer, default=587)
    use_tls = Column(Boolean, default=True)
    
    # ENCRYPTED Credentials
    encrypted_password = Column(Text, nullable=False)  # AES-256 encrypted IMAP/SMTP password
    
    # Connection Status
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)
    last_sync = Column(DateTime, nullable=True)
    sync_enabled = Column(Boolean, default=True)
    last_sync_status = Column(String, nullable=True)  # "success", "failed", etc
    sync_error = Column(Text, nullable=True)  # Last sync error message
    
    # Metadata
    total_emails = Column(Integer, default=0)
    unread_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "provider": self.provider,
            "email": self.email,
            "display_name": self.display_name,
            "imap_host": self.imap_host,
            "imap_port": self.imap_port,
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "use_tls": self.use_tls,
            "is_active": self.is_active,
            "is_primary": self.is_primary,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "last_sync_status": self.last_sync_status,
            "sync_enabled": self.sync_enabled,
            "total_emails": self.total_emails,
            "unread_count": self.unread_count,
            "created_at": self.created_at.isoformat(),
        }
