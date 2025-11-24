from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import jwt
from datetime import datetime, timedelta

from app.models.database import get_db
from app.models.user_models import User, UserEmailAccount
from app.core.security import create_access_token, verify_token, get_password_hash
from app.core.config import settings
from app.services.email_service import EmailService
from app.utils.validators import EmailValidator

router = APIRouter()
security = HTTPBearer()

# Dependency to get current user
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    try:
        token = credentials.credentials
        print(f"🔐 [get_current_user] Verifying token: {token[:20]}..." if token else "No token")
        
        payload = verify_token(token)
        if not payload:
            print("❌ [get_current_user] Token verification failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = payload.get("user_id")
        if not user_id:
            print("❌ [get_current_user] No user_id in token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        # Get user from database
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"❌ [get_current_user] User not found: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
            
        if not user.is_active:
            print(f"❌ [get_current_user] User inactive: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive",
            )

        print(f"✅ [get_current_user] User authenticated: {user.email}")
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [get_current_user] Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        )

# ========== DEBUG ENDPOINTS ==========

@router.get("/debug/users")
async def debug_users(db: AsyncSession = Depends(get_db)):
    """Debug endpoint to check all users in database"""
    try:
        print("🔍 [debug_users] Fetching all users from database")
        from sqlalchemy import select
        result = await db.execute(select(User))
        users = result.scalars().all()
        
        user_list = []
        for user in users:
            user_list.append({
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "is_verified": user.is_verified,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "password_hash": user.password_hash[:20] + "..." if user.password_hash else None
            })

        print(f"✅ [debug_users] Found {len(users)} users")
        return {
            "total_users": len(users),
            "users": user_list
        }
    except Exception as e:
        print(f"❌ [debug_users] Error: {e}")
        return {
            "error": str(e),
            "total_users": 0,
            "users": []
        }

@router.get("/debug/database")
async def debug_database(db: AsyncSession = Depends(get_db)):
    """Debug database connection and tables"""
    try:
        print("🔍 [debug_database] Testing database connection")
        # Test connection
        await db.execute("SELECT 1")
        
        # Check if users table exists and has data
        from sqlalchemy import text
        result = await db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'"))
        users_table_exists = result.scalar_one_or_none() is not None
        
        result = await db.execute(text("SELECT COUNT(*) FROM users"))
        user_count = result.scalar_one()
        
        print(f"✅ [debug_database] Database connected, users table: {users_table_exists}, user count: {user_count}")
        return {
            "database_connected": True,
            "users_table_exists": users_table_exists,
            "total_users": user_count,
            "database_type": "sqlite"
        }
    except Exception as e:
        print(f"❌ [debug_database] Error: {e}")
        return {
            "database_connected": False,
            "error": str(e)
        }

# ========== AUTH ENDPOINTS ==========

@router.post("/register")
async def register(
    user_data: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user"""
    try:
        email = user_data.get("email")
        password = user_data.get("password")
        full_name = user_data.get("full_name")
        
        print(f"🔍 [Register] Starting registration for: {email}")
        print(f"🔍 [Register] Received data: {user_data}")

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

        # Check password length for bcrypt (CRITICAL FIX)
        if len(password) > 72:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password cannot be longer than 72 characters"
            )

        # Check if user already exists
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"❌ [Register] User already exists: {email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

        print(f"✅ [Register] Creating new user: {email}")

        # Create new user
        user = User(
            email=email,
            full_name=full_name,
            is_verified=True,  # Auto-verify for immediate login
            is_active=True
        )

        print(f"🔍 [Register] User object created: {user.email}")

        # Set password with error handling
        try:
            user.set_password(password)
            print(f"🔍 [Register] Password set successfully for user")
        except Exception as password_error:
            print(f"❌ [Register] Password setting failed: {password_error}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Password error: {str(password_error)}"
            )

        # Generate verification token (but don't require verification for now)
        verification_token = user.generate_verification_token()
        print(f"🔍 [Register] Verification token generated")

        db.add(user)
        print(f"🔍 [Register] User added to session")

        try:
            await db.commit()
            print(f"✅ [Register] Database commit successful")
        except Exception as commit_error:
            print(f"❌ [Register] Database commit failed: {commit_error}")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save user to database"
            )

        await db.refresh(user)
        print(f"🔍 [Register] User refreshed from DB, ID: {user.id}")

        # Verify the user was actually saved
        result = await db.execute(select(User).where(User.email == email))
        saved_user = result.scalar_one_or_none()
        print(f"🔍 [Register] User verification - Found in DB: {saved_user is not None}")

        # Generate access token for immediate login (CRITICAL FIX)
        access_token = create_access_token(data={"user_id": user.id})
        print(f"🔐 [Register] Access token generated: {access_token[:20]}...")

        # Return user data
        user_response_data = {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_verified": user.is_verified,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }

        print(f"✅ [Register] Registration completed successfully for: {email}")
        print(f"📤 [Register] Returning response with access_token: {access_token[:20]}...")

        # CRITICAL: Return the access_token in the response
        return {
            "message": "User registered successfully",
            "user_id": user.id,
            "email": user.email,
            "access_token": access_token,  # THIS MUST BE INCLUDED
            "token_type": "bearer",
            "user": user_response_data
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"❌ [Register] Registration failed with error: {e}")
        import traceback
        print(f"❌ [Register] Stack trace: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

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
    try:
        email = credentials.get("email")
        password = credentials.get("password")
        
        print(f"🔑 [Login] Attempting login for: {email}")

        if not email or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and password are required"
            )

        from sqlalchemy import select
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        print(f"🔍 [Login] User found in DB: {user is not None}")
        if user:
            print(f"🔍 [Login] User details - ID: {user.id}, Verified: {user.is_verified}, Active: {user.is_active}")

        if not user:
            print(f"❌ [Login] User not found: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Check password
        password_valid = user.check_password(password)
        print(f"🔍 [Login] Password valid: {password_valid}")

        if not password_valid:
            print(f"❌ [Login] Invalid password for: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        if not user.is_active:
            print(f"❌ [Login] Account deactivated: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated"
            )

        # Update last login
        user.last_login = datetime.utcnow()
        await db.commit()
        print(f"✅ [Login] Last login updated for: {email}")

        # Generate access token
        access_token = create_access_token(data={"user_id": user.id})
        print(f"🔐 [Login] Access token generated for: {email}")

        # Return user data
        user_data = {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_verified": user.is_verified,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None
        }

        print(f"✅ [Login] Login successful for: {email}")
        print(f"📤 [Login] Returning access_token: {access_token[:20]}...")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_data
        }

    except Exception as e:
        print(f"❌ [Login] Login failed with error: {e}")
        import traceback
        print(f"❌ [Login] Stack trace: {traceback.format_exc()}")
        raise

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
    print(f"🔍 [me] Getting current user info for: {current_user.email}")

    # Return user data safely without relying on to_dict()
    user_data = {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_verified": current_user.is_verified,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None
    }

    print(f"✅ [me] Returning user data: {user_data}")
    return user_data

@router.post("/logout")
async def logout():
    """User logout"""
    print("🚪 [Logout] User logging out")
    return {
        "message": "Successfully logged out",
        "success": True
    }

@router.post("/refresh")
async def refresh_token(current_user: User = Depends(get_current_user)):
    """Refresh access token"""
    print(f"🔄 [refresh] Refreshing token for: {current_user.email}")
    new_token = create_access_token(data={"user_id": current_user.id})
    return {
        "access_token": new_token,
        "token_type": "bearer"
    }

# Email sending functions (to be implemented with real email service)
async def send_verification_email(email: str, name: str, token: str):
    """Send verification email"""
    verification_url = f"http://localhost:3000/verify-email?token={token}"
    print(f"📧 Verification email sent to {email}: {verification_url}")
    # TODO: Integrate with real email service (SendGrid, SMTP, etc.)

async def send_password_reset_email(email: str, name: str, token: str):
    """Send password reset email"""
    reset_url = f"http://localhost:3000/reset-password?token={token}"
    print(f"📧 Password reset email sent to {email}: {reset_url}")
    # TODO: Integrate with real email service
