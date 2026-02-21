"""Auth API — login, logout, profile endpoints."""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError, jwt

from app.core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from app.persistence.db import get_connection

router = APIRouter(prefix="/auth", tags=["auth"])

_bearer = HTTPBearer(auto_error=False)


# ------------------------------------------------------------------
# Password hashing (Direct bcrypt to avoid passlib compatibility issues)
# ------------------------------------------------------------------
def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


# ------------------------------------------------------------------
# Pydantic schemas
# ------------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str
    password: str


class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None


# ------------------------------------------------------------------
# JWT helpers
# ------------------------------------------------------------------
def _create_token(user_id: str, username: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")


# ------------------------------------------------------------------
# Dependency: get current user from Bearer token
# ------------------------------------------------------------------
def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer)) -> dict:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return _decode_token(credentials.credentials)


def optional_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer)) -> Optional[dict]:
    if not credentials:
        return None
    try:
        return _decode_token(credentials.credentials)
    except HTTPException:
        return None


# ------------------------------------------------------------------
# DB helpers
# ------------------------------------------------------------------
def _get_user_by_username(username: str) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def _get_user_by_id(user_id: str) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------
@router.post("/login")
def login(body: LoginRequest):
    user = _get_user_by_username(body.username)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = _create_token(user["id"], user["username"], user["role"])
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "display_name": user.get("display_name"),
            "email": user.get("email"),
        },
    }


@router.post("/logout")
def logout(current_user: dict = Depends(get_current_user)):
    # Stateless JWT — just acknowledge. Client discards token.
    return {"detail": "Logged out successfully"}


@router.get("/profile")
def get_profile(current_user: dict = Depends(get_current_user)):
    user = _get_user_by_id(current_user["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "display_name": user.get("display_name"),
        "email": user.get("email"),
    }


@router.put("/profile")
def update_profile(body: ProfileUpdateRequest, current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    conn.execute(
        "UPDATE users SET display_name = ?, email = ? WHERE id = ?",
        (body.display_name, body.email, current_user["sub"]),
    )
    conn.commit()
    conn.close()
    return {"detail": "Profile updated"}
