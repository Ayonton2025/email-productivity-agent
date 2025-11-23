from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import jwt

from app.models.database import get_db
from app.models.user_models import User, UserEmailAccount
from app.core.security import create_access_token, verify_token, get_password_hash
from app.core.config import settings
from app.services.email_service import EmailService
from app.utils.validators import EmailValidator
from datetime import datetime


router = APIRouter()
security = HTTPBearer()

# Dependency to get current user
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    
    # Get user from database
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    
    return user

@router.post("/register")
async def register(
    user_data: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user"""
    email = user_data.get("email")
    password = user_data.get("password")
    full_name = user_data.get("full_name")

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )

    if not EmailValidator.validate_email_format(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )

    # Check if user already exists
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.email == email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # Create new user
    user = User(
        email=email,
        full_name=full_name
    )
    user.set_password(password)
    
    # Generate verification token
    verification_token = user.generate_verification_token()
    
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Send verification email (in background)
    background_tasks.add_task(
        send_verification_email,
        user.email,
        user.full_name,
        verification_token
    )

    return {
        "message": "User registered successfully. Please check your email for verification.",
        "user_id": user.id,
        "email": user.email
    }

@router.post("/verify-email")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    """Verify user email"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token"
            )
        
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.verification_token != token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token"
            )
        
        user.is_verified = True
        user.verification_token = None
        await db.commit()
        
        return {"message": "Email verified successfully"}
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )

@router.post("/login")
async def login(credentials: dict, db: AsyncSession = Depends(get_db)):
    """User login"""
    email = credentials.get("email")
    password = credentials.get("password")

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )

    from sqlalchemy import select
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not user.check_password(password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated"
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please verify your email first"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()

    # Generate access token
    access_token = create_access_token(data={"user_id": user.id})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user.to_dict()
    }

@router.post("/forgot-password")
async def forgot_password(
    email_data: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Request password reset"""
    email = email_data.get("email")
    
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if user:
        reset_token = user.generate_reset_token()
        await db.commit()
        
        # Send reset email (in background)
        background_tasks.add_task(
            send_password_reset_email,
            user.email,
            user.full_name,
            reset_token
        )
    
    return {
        "message": "If the email exists, a password reset link has been sent"
    }

@router.post("/reset-password")
async def reset_password(reset_data: dict, db: AsyncSession = Depends(get_db)):
    """Reset password with token"""
    token = reset_data.get("token")
    new_password = reset_data.get("new_password")
    
    if not token or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token and new password are required"
        )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user or user.reset_token != token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )
        
        user.set_password(new_password)
        user.reset_token = None
        await db.commit()
        
        return {"message": "Password reset successfully"}
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )

@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user.to_dict()

# Email sending functions (to be implemented with real email service)
async def send_verification_email(email: str, name: str, token: str):
    """Send verification email"""
    verification_url = f"http://localhost:3000/verify-email?token={token}"
    print(f"Verification email sent to {email}: {verification_url}")
    # TODO: Integrate with real email service (SendGrid, SMTP, etc.)

async def send_password_reset_email(email: str, name: str, token: str):
    """Send password reset email"""
    reset_url = f"http://localhost:3000/reset-password?token={token}"
    print(f"Password reset email sent to {email}: {reset_url}")
    # TODO: Integrate with real email service