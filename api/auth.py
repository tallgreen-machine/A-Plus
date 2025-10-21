"""
Authentication API endpoints
Handles user login, logout, registration, and session management
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Optional
from datetime import timedelta
import psycopg2.extras
import logging

from database import get_database
from auth_utils import create_access_token, hash_password, verify_password, ACCESS_TOKEN_EXPIRE_MINUTES

# Configure logging
log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    display_name: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: dict

class UserResponse(BaseModel):
    id: int
    username: str
    display_name: Optional[str]
    email: Optional[str]
    is_active: bool

@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest, db=Depends(get_database)):
    """Authenticate user and return access token"""
    try:
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                "SELECT id, username, password_hash, display_name, email, is_active FROM users WHERE username = %s",
                (login_data.username,)
            )
            user = cur.fetchone()
            
            if not user or not verify_password(login_data.password, user['password_hash']):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password"
                )
            
            if not user['is_active']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inactive user account"
                )
            
            # Create access token
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user['username'], "user_id": user['id']},
                expires_delta=access_token_expires
            )
            
            # Log successful login
            log.info(f"User {user['username']} logged in successfully")
            
            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                user={
                    "id": user['id'],
                    "username": user['username'],
                    "display_name": user['display_name'],
                    "email": user['email'],
                    "is_active": user['is_active']
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@router.post("/register", response_model=UserResponse)
async def register(register_data: RegisterRequest, db=Depends(get_database)):
    """Register a new user account"""
    try:
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            # Check if username already exists
            cur.execute("SELECT id FROM users WHERE username = %s", (register_data.username,))
            if cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered"
                )
            
            # Hash password and create user
            hashed_password = hash_password(register_data.password)
            cur.execute(
                """
                INSERT INTO users (username, password_hash, email, display_name)
                VALUES (%s, %s, %s, %s)
                RETURNING id, username, display_name, email, is_active
                """,
                (
                    register_data.username,
                    hashed_password,
                    register_data.email,
                    register_data.display_name or register_data.username
                )
            )
            
            user = cur.fetchone()
            db.commit()
            
            log.info(f"New user registered: {user['username']}")
            
            return UserResponse(
                id=user['id'],
                username=user['username'],
                display_name=user['display_name'],
                email=user['email'],
                is_active=user['is_active']
            )
            
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

# Temporary test endpoint without authentication
@router.get("/test-users")
async def test_users(db=Depends(get_database)):
    """Test endpoint to verify database connection and user data"""
    try:
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT id, username, display_name FROM users LIMIT 5")
            users = cur.fetchall()
            return {"users": [dict(user) for user in users]}
    except Exception as e:
        return {"error": str(e)}

@router.get("/users", response_model=list[UserResponse])
async def list_users(db=Depends(get_database)):
    """List all users (for user switching in frontend)"""
    try:
        with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                "SELECT id, username, display_name, email, is_active FROM users WHERE is_active = true ORDER BY username"
            )
            users = cur.fetchall()
            
            return [
                UserResponse(
                    id=user['id'],
                    username=user['username'],
                    display_name=user['display_name'],
                    email=user['email'],
                    is_active=user['is_active']
                )
                for user in users
            ]
            
    except Exception as e:
        log.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve users")

@router.post("/logout")
async def logout():
    """Logout endpoint (client-side token deletion)"""
    return {"message": "Logged out successfully"}