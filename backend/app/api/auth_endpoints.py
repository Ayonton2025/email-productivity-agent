import logging
from datetime import datetime
from typing import Optional

import jwt
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from app.core.config import settings
from app.core.security import create_access_token, verify_token
from app.models.database import get_db
from app.models.user_models import User
from app.utils.validators import EmailValidator

router = APIRouter()
logger = logging.getLogger(__name__)
security = HTTPBearer()


def _is_super_admin_email(email: Optional[str]) -> bool:
    if not email:
        return False
    allowed = {e.strip().lower() for e in (settings.ADMIN_EMAILS or "").split(",") if e.strip()}
    return email.lower() in allowed


# Dependency to get current user
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        token = credentials.credentials
        logger.debug("Authenticating bearer token", extra={"token_present": bool(token)})

        payload = verify_token(token)
        if not payload:
            logger.error("❌ [get_current_user] Token verification failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = payload.get("user_id")
        if not user_id:
            logger.info("❌ [get_current_user] No user_id in token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        # Get user from database
        from sqlalchemy import select

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            logger.error(f"❌ [get_current_user] User not found: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        if not user.is_active:
            logger.error(f"❌ [get_current_user] User inactive: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive",
            )

        logger.info(f"✅ [get_current_user] User authenticated: {user.email}")
        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [get_current_user] Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        )


# ========== DEBUG ENDPOINTS ==========


@router.get("/debug/users")
async def debug_users(db: AsyncSession = Depends(get_db)):
    """Debug endpoint to check all users in database"""
    try:
        logger.info("🔍 [debug_users] Fetching all users from database")
        from sqlalchemy import select

        result = await db.execute(select(User))
        users = result.scalars().all()

        user_list = []
        for user in users:
            user_list.append(
                {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "is_verified": user.is_verified,
                    "is_active": user.is_active,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "password_hash": user.password_hash[:20] + "..."
                    if user.password_hash
                    else None,
                }
            )

        logger.info(f"✅ [debug_users] Found {len(users)} users")
        return {"total_users": len(users), "users": user_list}
    except Exception as e:
        logger.error(f"❌ [debug_users] Error: {e}")
        return {"error": str(e), "total_users": 0, "users": []}


@router.get("/debug/database")
async def debug_database(db: AsyncSession = Depends(get_db)):
    """Debug database connection and tables"""
    try:
        logger.info("🔍 [debug_database] Testing database connection")
        # Test connection
        await db.execute("SELECT 1")

        # Check if users table exists and has data
        from sqlalchemy import text

        result = await db.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        )
        users_table_exists = result.scalar_one_or_none() is not None

        result = await db.execute(text("SELECT COUNT(*) FROM users"))
        user_count = result.scalar_one()

        logger.info(
            f"✅ [debug_database] Database connected, users table: {users_table_exists}, user count: {user_count}"
        )
        return {
            "database_connected": True,
            "users_table_exists": users_table_exists,
            "total_users": user_count,
            "database_type": "sqlite",
        }
    except Exception as e:
        logger.error(f"❌ [debug_database] Error: {e}")
        return {"database_connected": False, "error": str(e)}


# ========== AUTH ENDPOINTS ==========


@router.post("/register")
async def register(
    user_data: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user"""
    try:
        email = str(user_data.email)
        password = user_data.password
        full_name = user_data.full_name

        logger.info(f"🔍 [Register] Starting registration for: {email}")
        logger.info("Registration request received", extra={"email": email})

        if not email or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email and password are required"
            )

        if not EmailValidator.validate_email_format(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format"
            )

        # Check password length for bcrypt (CRITICAL FIX)
        if len(password) > 72:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password cannot be longer than 72 characters",
            )

        # Check if user already exists
        from sqlalchemy import select

        result = await db.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            logger.info(f"❌ [Register] User already exists: {email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists",
            )

        logger.info(f"✅ [Register] Creating new user: {email}")

        # Create new user
        user = User(
            email=email,
            full_name=full_name,
            is_verified=True,  # Auto-verify for immediate login
            is_active=True,
        )

        logger.info(f"🔍 [Register] User object created: {user.email}")

        # Set password with error handling
        try:
            user.set_password(password)
            logger.info("🔍 [Register] Password set successfully for user")
        except Exception as password_error:
            logger.error(f"❌ [Register] Password setting failed: {password_error}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Password error: {str(password_error)}",
            )

        # Generate verification token (but don't require verification for now)
        _verification_token = user.generate_verification_token()
        logger.info("🔍 [Register] Verification token generated")

        db.add(user)
        logger.info("🔍 [Register] User added to session")

        try:
            await db.commit()
            logger.info("✅ [Register] Database commit successful")
        except Exception as commit_error:
            logger.error(f"❌ [Register] Database commit failed: {commit_error}")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save user to database",
            )

        await db.refresh(user)
        logger.info(f"🔍 [Register] User refreshed from DB, ID: {user.id}")

        # Verify the user was actually saved
        result = await db.execute(select(User).where(User.email == email))
        saved_user = result.scalar_one_or_none()
        logger.info(f"🔍 [Register] User verification - Found in DB: {saved_user is not None}")

        # Generate access token for immediate login (CRITICAL FIX)
        access_token = create_access_token(data={"user_id": user.id})
        logger.info("Registration access token generated", extra={"user_id": str(user.id)})

        # Return user data
        user_response_data = {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_verified": user.is_verified,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "is_super_admin": _is_super_admin_email(user.email),
        }

        logger.info(f"✅ [Register] Registration completed successfully for: {email}")
        logger.info("Registration response prepared", extra={"user_id": str(user.id)})

        # CRITICAL: Return the access_token in the response
        return {
            "message": "User registered successfully",
            "user_id": user.id,
            "email": user.email,
            "access_token": access_token,  # THIS MUST BE INCLUDED
            "token_type": "bearer",
            "user": user_response_data,
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"❌ [Register] Registration failed with error: {e}")
        import traceback

        logger.info(f"❌ [Register] Stack trace: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}",
        )


@router.post("/verify-email")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    """Verify user email"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token"
            )

        from sqlalchemy import select

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if user.verification_token != token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token"
            )

        user.is_verified = True
        user.verification_token = None
        await db.commit()

        return {"message": "Email verified successfully"}

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Verification token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token"
        )


@router.post("/login")
async def login(credentials: LoginRequest, db: AsyncSession = Depends(get_db)):
    """User login"""
    try:
        email = str(credentials.email)
        password = credentials.password

        logger.info(f"🔑 [Login] Attempting login for: {email}")

        if not email or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email and password are required"
            )

        from sqlalchemy import select

        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        logger.info(f"🔍 [Login] User found in DB: {user is not None}")
        if user:
            logger.info(
                f"🔍 [Login] User details - ID: {user.id}, Verified: {user.is_verified}, Active: {user.is_active}"
            )

        if not user:
            logger.error(f"❌ [Login] User not found: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
            )

        # Check password
        password_valid = user.check_password(password)
        logger.info(f"🔍 [Login] Password valid: {password_valid}")

        if not password_valid:
            logger.error(f"❌ [Login] Invalid password for: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
            )

        if not user.is_active:
            logger.info(f"❌ [Login] Account deactivated: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is deactivated"
            )

        # Update last login
        user.last_login = datetime.utcnow()
        await db.commit()
        logger.info(f"✅ [Login] Last login updated for: {email}")

        # Generate access token
        access_token = create_access_token(data={"user_id": user.id})
        logger.info(f"🔐 [Login] Access token generated for: {email}")

        # Return user data
        user_data = {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_verified": user.is_verified,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "is_super_admin": _is_super_admin_email(user.email),
        }

        logger.info(f"✅ [Login] Login successful for: {email}")
        logger.info("Login response prepared", extra={"user_id": str(user.id)})

        return {"access_token": access_token, "token_type": "bearer", "user": user_data}

    except Exception as e:
        logger.error(f"❌ [Login] Login failed with error: {e}")
        import traceback

        logger.info(f"❌ [Login] Stack trace: {traceback.format_exc()}")
        raise


@router.post("/forgot-password")
async def forgot_password(
    email_data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Request password reset"""
    email = str(email_data.email)
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        reset_token = user.generate_reset_token()
        await db.commit()

        # Send reset email (in background)
        background_tasks.add_task(
            send_password_reset_email, user.email, user.full_name, reset_token
        )

    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/reset-password")
async def reset_password(reset_data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Reset password with token"""
    token = reset_data.token
    new_password = reset_data.new_password

    if not token or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Token and new password are required"
        )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")

        from sqlalchemy import select

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or user.reset_token != token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token"
            )

        user.set_password(new_password)
        user.reset_token = None
        await db.commit()

        return {"message": "Password reset successfully"}

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Reset token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token")


@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    logger.info(f"🔍 [me] Getting current user info for: {current_user.email}")

    # Return user data safely without relying on to_dict()
    user_data = {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_verified": current_user.is_verified,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
        "is_super_admin": _is_super_admin_email(current_user.email),
    }

    logger.debug("Current-user response prepared", extra={"user_id": str(current_user.id)})
    return user_data


@router.post("/logout")
async def logout():
    """User logout"""
    logger.info("🚪 [Logout] User logging out")
    return {"message": "Successfully logged out", "success": True}


@router.post("/refresh")
async def refresh_token(current_user: User = Depends(get_current_user)):
    """Refresh access token"""
    logger.info(f"🔄 [refresh] Refreshing token for: {current_user.email}")
    new_token = create_access_token(data={"user_id": current_user.id})
    return {"access_token": new_token, "token_type": "bearer"}


# Email sending functions (to be implemented with real email service)
async def send_verification_email(email: str, name: str, token: str):
    """Send verification email"""
    logger.info("Verification email prepared", extra={"email": email})
    # TODO: Integrate with real email service (SendGrid, SMTP, etc.)


async def send_password_reset_email(email: str, name: str, token: str):
    """Send password reset email"""
    logger.info("Password reset email prepared", extra={"email": email})
    # TODO: Integrate with real email service
