"""백엔드 API 테스트용 fixtures."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from jose import jwt

from backend.main import app
from backend.dependencies import get_current_user

_SECRET_KEY = "test-secret-key-for-testing"
_ALGORITHM = "HS256"


def _make_token(user_id: int = 1, username: str = "admin", name: str = "관리자", role: str = "ADMIN") -> str:
    """테스트용 JWT 생성."""
    payload = {
        "sub": str(user_id),
        "user_id": user_id,
        "username": username,
        "name": name,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=8),
    }
    return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)


def _get_current_user_override():
    """get_current_user 의존성 오버라이드 — 테스트용 유저 반환."""
    return {
        "user_id": 1,
        "username": "admin",
        "name": "관리자",
        "role": "ADMIN",
    }


@pytest.fixture
def client():
    """인증 우회 TestClient."""
    app.dependency_overrides[get_current_user] = _get_current_user_override
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def unauth_client():
    """인증 오버라이드 없는 TestClient (401 테스트용)."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def auth_cookies():
    """유효한 JWT 쿠키 딕셔너리 반환."""
    with patch.dict("os.environ", {
        "JWT_SECRET_KEY": _SECRET_KEY,
        "JWT_ALGORITHM": _ALGORITHM,
    }):
        token = _make_token()
    return {"access_token": token}
