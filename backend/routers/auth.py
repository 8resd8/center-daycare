"""인증 라우터 — 로그인/로그아웃/토큰갱신/현재 사용자 조회"""

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
ACCESS_EXPIRE_HOURS = int(os.getenv("JWT_ACCESS_EXPIRE_HOURS", "2"))
REFRESH_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_EXPIRE_DAYS", "7"))

_SAME_CREDENTIALS_MSG = "아이디 또는 비밀번호가 올바르지 않습니다."


def _make_token(user: dict, expire: datetime) -> str:
    payload = {
        "sub": str(user["user_id"]),
        "user_id": user["user_id"],
        "username": user["username"],
        "name": user["name"],
        "role": user["role"],
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _make_refresh_token(user: dict, expire: datetime) -> str:
    """리프레시 토큰 — sub + exp만 포함 (최소 정보)."""
    payload = {
        "sub": str(user["user_id"]),
        "user_id": user["user_id"],
        "type": "refresh",
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _is_production() -> bool:
    return os.getenv("APP_ENV", "development") == "production"


def _set_access_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="strict",
        secure=_is_production(),
        max_age=ACCESS_EXPIRE_HOURS * 3600,
        path="/",
    )


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        samesite="strict",
        secure=_is_production(),
        max_age=REFRESH_EXPIRE_DAYS * 86400,
        path="/api/auth",   # refresh 엔드포인트에만 전송
    )


def _clear_cookies(response: Response) -> None:
    for key, path in [("access_token", "/"), ("refresh_token", "/api/auth")]:
        response.set_cookie(
            key=key, value="", httponly=True,
            samesite="strict", max_age=0, path=path,
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
        if hashlib.sha256(body.password.encode()).hexdigest() == stored_hash:
            verified = True
            needs_migration = True

    if not verified:
        # 3차: 평문 레거시 검증 (초기 데이터 마이그레이션용)
        if body.password == stored_hash:
            verified = True
            needs_migration = True

    if not verified:
        raise HTTPException(status_code=401, detail=_SAME_CREDENTIALS_MSG)

    # 레거시 → bcrypt 자동 마이그레이션
    if needs_migration:
        repo.update_password(user["user_id"], pwd_context.hash(body.password))

    now = datetime.now(timezone.utc)
    access_token = _make_token(user, now + timedelta(hours=ACCESS_EXPIRE_HOURS))
    refresh_token = _make_refresh_token(user, now + timedelta(days=REFRESH_EXPIRE_DAYS))

    _set_access_cookie(response, access_token)
    _set_refresh_cookie(response, refresh_token)

    return UserInfo(
        user_id=user["user_id"],
        username=user["username"],
        name=user["name"],
        role=user["role"],
    )


@router.post("/auth/refresh", response_model=UserInfo)
def refresh_token(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    repo: UserRepository = Depends(get_user_repo),
):
    """리프레시 토큰으로 새 액세스 토큰 발급."""
    if not refresh_token:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    except JWTError:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")

    user = repo.get_user(payload["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")

    # username, role은 DB에서 다시 읽어야 하므로 별도 조회
    full_user = repo.find_by_user_id_with_auth(payload["user_id"])
    if not full_user:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")

    now = datetime.now(timezone.utc)
    new_access = _make_token(full_user, now + timedelta(hours=ACCESS_EXPIRE_HOURS))
    _set_access_cookie(response, new_access)

    return UserInfo(
        user_id=full_user["user_id"],
        username=full_user["username"],
        name=full_user["name"],
        role=full_user["role"],
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
    _clear_cookies(response)
    return {"message": "로그아웃 완료"}
