"""인증 라우터 — 로그인/로그아웃/현재 사용자 조회"""

import os
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Cookie
from jose import jwt, JWTError
from passlib.context import CryptContext
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.dependencies import get_user_repo
from backend.schemas.auth import LoginRequest, UserInfo
from modules.repositories.user import UserRepository

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production-use-random-32bytes")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "8"))

_SAME_CREDENTIALS_MSG = "아이디 또는 비밀번호가 올바르지 않습니다."


def _create_token(user: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=EXPIRE_HOURS)
    payload = {
        "sub": str(user["user_id"]),
        "user_id": user["user_id"],
        "username": user["username"],
        "name": user["name"],
        "role": user["role"],
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _set_auth_cookie(response: Response, token: str) -> None:
    is_production = os.getenv("APP_ENV", "development") == "production"
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="strict",
        secure=is_production,
        max_age=EXPIRE_HOURS * 3600,
        path="/",
    )


@router.post("/auth/login", response_model=UserInfo)
@limiter.limit("5/minute")
def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    repo: UserRepository = Depends(get_user_repo),
):
    user = repo.find_by_username(body.username)
    if not user:
        raise HTTPException(status_code=401, detail=_SAME_CREDENTIALS_MSG)

    stored_hash: str = user["password"] or ""
    verified = False
    needs_migration = False

    # 1차: bcrypt 검증
    try:
        verified = pwd_context.verify(body.password, stored_hash)
    except Exception:
        verified = False

    if not verified:
        # 2차: SHA256 레거시 검증
        sha_hash = hashlib.sha256(body.password.encode()).hexdigest()
        if sha_hash == stored_hash:
            verified = True
            needs_migration = True

    if not verified:
        # 3차: 평문 레거시 검증 (초기 데이터 마이그레이션용)
        if body.password == stored_hash:
            verified = True
            needs_migration = True

    if not verified:
        raise HTTPException(status_code=401, detail=_SAME_CREDENTIALS_MSG)

    # SHA256 → bcrypt 자동 마이그레이션
    if needs_migration:
        new_hash = pwd_context.hash(body.password)
        repo.update_password(user["user_id"], new_hash)

    token = _create_token(user)
    _set_auth_cookie(response, token)

    return UserInfo(
        user_id=user["user_id"],
        username=user["username"],
        name=user["name"],
        role=user["role"],
    )


@router.get("/auth/me", response_model=UserInfo)
def get_me(access_token: Optional[str] = Cookie(None)):
    if not access_token:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        return UserInfo(
            user_id=payload["user_id"],
            username=payload["username"],
            name=payload["name"],
            role=payload["role"],
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")


@router.post("/auth/logout")
def logout(response: Response):
    response.set_cookie(
        key="access_token",
        value="",
        httponly=True,
        samesite="strict",
        max_age=0,
        path="/",
    )
    return {"message": "로그아웃 완료"}
