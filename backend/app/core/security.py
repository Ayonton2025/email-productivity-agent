from typing import Optional, Union, Any
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets

# Security configuration
SECRET_KEY = secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

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