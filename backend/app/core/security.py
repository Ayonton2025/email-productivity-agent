from typing import Optional, Union, Any
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets
import json
from cryptography.fernet import Fernet
import os
import base64
import hashlib
import logging

# Logger for modules that import `logger` from security
logger = logging.getLogger("email_productivity_agent")
if not logger.handlers:
    # Basic configuration for the logger to ensure it prints in containers
    LOG_LEVEL_NAME = os.environ.get("LOG_LEVEL", "INFO").upper()
    LOG_LEVEL = getattr(logging, LOG_LEVEL_NAME, logging.INFO)
    logging.basicConfig(level=LOG_LEVEL)

# Import settings to use the same SECRET_KEY
from app.core.config import settings

# Security configuration - use the SAME secret key from config
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # Increased to 24 hours for development stability

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============== PASSWORD & TOKEN UTILITIES ==============

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"❌ [Security] Password verification failed: {e}")
        return False

def get_password_hash(password: str) -> str:
    """Generate password hash with bcrypt length validation"""
    # bcrypt has a 72 byte limit, so validate password length
    if len(password) > 72:
        raise ValueError("Password too long for bcrypt hashing (max 72 characters)")
    
    try:
        hashed = pwd_context.hash(password)
        print(f"🔑 [Security] Password hashed successfully")
        return hashed
    except Exception as e:
        print(f"❌ [Security] Password hashing failed: {e}")
        raise

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    try:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        print(f"🔐 [Security] Access token created for user_id: {data.get('user_id')}")
        return encoded_jwt
    except Exception as e:
        print(f"❌ [Security] Token creation failed: {e}")
        raise

def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"✅ [Security] Token verified for user_id: {payload.get('user_id')}")
        return payload
    except JWTError as e:
        print(f"❌ [Security] Token verification failed: {e}")
        return None
    except Exception as e:
        print(f"❌ [Security] Token verification error: {e}")
        return None

# ============== EMAIL CREDENTIAL ENCRYPTION ==============

def _get_encryption_key() -> bytes:
    """Get or generate encryption key for AES-256"""
    enc_key = settings.ENCRYPTION_KEY
    
    # Ensure key is exactly 32 bytes for AES-256
    if isinstance(enc_key, str):
        # If it's a string, hash it to 32 bytes
        key_bytes = hashlib.sha256(enc_key.encode()).digest()
    else:
        key_bytes = enc_key
    
    # Encode to base64 for Fernet
    return base64.urlsafe_b64encode(key_bytes)

def encrypt_credential(credential: str) -> str:
    """Encrypt email credential (password) using AES-256"""
    try:
        key = _get_encryption_key()
        f = Fernet(key)
        encrypted = f.encrypt(credential.encode())
        return encrypted.decode()
    except Exception as e:
        print(f"❌ [Security] Credential encryption failed: {e}")
        raise

def decrypt_credential(encrypted_credential: str) -> str:
    """Decrypt email credential using AES-256"""
    try:
        key = _get_encryption_key()
        f = Fernet(key)
        decrypted = f.decrypt(encrypted_credential.encode())
        return decrypted.decode()
    except Exception as e:
        print(f"❌ [Security] Credential decryption failed: {e}")
        raise

# ============== SANITIZATION & VALIDATION ==============

def sanitize_email_content(content: str) -> str:
    """Sanitize email content to prevent injection attacks"""
    if not content:
        return ""
    
    # Remove potentially dangerous characters/patterns
    sanitized = content.replace('<script>', '').replace('</script>', '')
    sanitized = sanitized.replace('javascript:', '')
    sanitized = sanitized.replace('onerror=', '')
    sanitized = sanitized.replace('onload=', '')
    
    return sanitized

def validate_email_address(email: str) -> bool:
    """Basic email validation"""
    if not email or '@' not in email:
        return False
    
    # Simple regex-like check without using re module
    parts = email.split('@')
    if len(parts) != 2:
        return False
    
    local_part, domain = parts
    if not local_part or not domain or '.' not in domain:
        return False
    
    return True

def safe_json_parse(json_str: str) -> Optional[dict]:
    """Safely parse JSON string"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return None


# ============== AUTH DEPENDENCIES ==============
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

security = HTTPBearer()


async def _lazy_get_db():
    """Lazily import and delegate to app.models.database.get_db to avoid circular imports."""
    # Import inside function to break circular import at module import time
    from app.models.database import get_db
    async for session in get_db():
        yield session

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(_lazy_get_db)
):
    """
    FastAPI dependency to verify JWT token and return User model.
    This is intentionally lightweight and raises HTTPException on failure.
    """
    try:
        token = credentials.credentials
        if not token:
            logger.warning("No authentication token provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )

        payload = verify_token(token)
        if not payload:
            logger.warning("Token verification failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )

        user_id = payload.get("user_id")
        if not user_id:
            logger.warning("Token payload missing user_id")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        # Import here to avoid circular import at module level
        from sqlalchemy import select
        from app.models.user_models import User

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"Authenticated user not found: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        if not getattr(user, "is_active", True):
            logger.warning(f"Inactive user attempted access: {getattr(user, 'email', user_id)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive",
            )

        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        )
