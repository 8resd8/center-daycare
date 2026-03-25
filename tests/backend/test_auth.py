"""인증 엔드포인트 테스트."""

import hashlib
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from passlib.context import CryptContext

from backend.main import app
from backend.dependencies import get_user_repo


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """각 테스트 전후 Rate Limiter 스토리지 초기화."""
    import backend.routers.auth as auth_module
    try:
        auth_module.limiter._storage.reset()
    except Exception:
        pass
    yield
    try:
        auth_module.limiter._storage.reset()
    except Exception:
        pass

_PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")
_TEST_SECRET = "test-secret-key-for-unit-tests-only"
_ALGORITHM = "HS256"


@pytest.fixture(autouse=True)
def patch_jwt_secret():
    """테스트 전용 JWT secret으로 auth 모듈을 패치 (load_dotenv 영향 차단)."""
    import backend.routers.auth as auth_module
    import backend.dependencies as deps_module
    original_auth = auth_module.SECRET_KEY
    original_deps = deps_module._SECRET_KEY
    auth_module.SECRET_KEY = _TEST_SECRET
    deps_module._SECRET_KEY = _TEST_SECRET
    yield
    auth_module.SECRET_KEY = original_auth
    deps_module._SECRET_KEY = original_deps


def _make_user(
    user_id: int = 1,
    username: str = "testuser",
    name: str = "테스트",
    role: str = "EMPLOYEE",
    raw_password: str = "password123",
    use_bcrypt: bool = True,
) -> dict:
    pw_hash = (
        _PWD_CONTEXT.hash(raw_password)
        if use_bcrypt
        else hashlib.sha256(raw_password.encode()).hexdigest()
    )
    return {
        "user_id": user_id,
        "username": username,
        "name": name,
        "role": role,
        "password": pw_hash,
        "work_status": "재직",
    }


def _mock_repo(user: dict | None, update_returns: int = 1) -> MagicMock:
    """find_by_username/update_password를 가진 mock repo."""
    repo = MagicMock()
    repo.find_by_username.return_value = user
    repo.update_password.return_value = update_returns
    return repo


# ── 로그인 성공 케이스 ──────────────────────────────────────────────


class TestLogin:
    def test_login_success_returns_user_info(self):
        user = _make_user()
        mock_r = _mock_repo(user)
        app.dependency_overrides[get_user_repo] = lambda: mock_r
        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                res = client.post(
                    "/api/auth/login",
                    json={"username": "testuser", "password": "password123"},
                )
        finally:
            app.dependency_overrides.pop(get_user_repo, None)

        assert res.status_code == 200
        data = res.json()
        assert data["username"] == "testuser"
        assert data["name"] == "테스트"
        assert "password" not in data

    def test_login_sets_httponly_cookie(self):
        user = _make_user()
        mock_r = _mock_repo(user)
        app.dependency_overrides[get_user_repo] = lambda: mock_r
        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                res = client.post(
                    "/api/auth/login",
                    json={"username": "testuser", "password": "password123"},
                )
        finally:
            app.dependency_overrides.pop(get_user_repo, None)

        assert res.status_code == 200
        assert "access_token" in res.cookies

    def test_login_wrong_password_returns_401(self):
        user = _make_user()
        mock_r = _mock_repo(user)
        app.dependency_overrides[get_user_repo] = lambda: mock_r
        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                res = client.post(
                    "/api/auth/login",
                    json={"username": "testuser", "password": "wrong_pw"},
                )
        finally:
            app.dependency_overrides.pop(get_user_repo, None)

        assert res.status_code == 401
        assert res.json()["detail"] == "아이디 또는 비밀번호가 올바르지 않습니다."

    def test_login_unknown_user_returns_401(self):
        mock_r = _mock_repo(None)
        app.dependency_overrides[get_user_repo] = lambda: mock_r
        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                res = client.post(
                    "/api/auth/login",
                    json={"username": "nobody", "password": "pass"},
                )
        finally:
            app.dependency_overrides.pop(get_user_repo, None)

        assert res.status_code == 401
        assert res.json()["detail"] == "아이디 또는 비밀번호가 올바르지 않습니다."

    def test_wrong_pw_and_unknown_user_same_message(self):
        """존재하지 않는 유저와 잘못된 비밀번호 메시지가 동일해야 한다."""
        user = _make_user()

        app.dependency_overrides[get_user_repo] = lambda: _mock_repo(user)
        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                res_wrong_pw = client.post(
                    "/api/auth/login",
                    json={"username": "testuser", "password": "bad"},
                )
        finally:
            app.dependency_overrides.pop(get_user_repo, None)

        app.dependency_overrides[get_user_repo] = lambda: _mock_repo(None)
        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                res_no_user = client.post(
                    "/api/auth/login",
                    json={"username": "ghost", "password": "bad"},
                )
        finally:
            app.dependency_overrides.pop(get_user_repo, None)

        assert res_wrong_pw.json()["detail"] == res_no_user.json()["detail"]


# ── SHA256 → bcrypt 자동 마이그레이션 ──────────────────────────────

class TestPasswordMigration:
    def test_sha256_password_migrated_to_bcrypt(self):
        user = _make_user(raw_password="password123", use_bcrypt=False)
        mock_r = _mock_repo(user)
        app.dependency_overrides[get_user_repo] = lambda: mock_r
        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                res = client.post(
                    "/api/auth/login",
                    json={"username": "testuser", "password": "password123"},
                )
        finally:
            app.dependency_overrides.pop(get_user_repo, None)

        assert res.status_code == 200
        # update_password가 호출되고 새 hash가 bcrypt임을 확인
        mock_r.update_password.assert_called_once()
        new_hash = mock_r.update_password.call_args[0][1]
        assert _PWD_CONTEXT.verify("password123", new_hash)

    def test_sha256_wrong_password_returns_401(self):
        user = _make_user(raw_password="correct", use_bcrypt=False)
        mock_r = _mock_repo(user)
        app.dependency_overrides[get_user_repo] = lambda: mock_r
        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                res = client.post(
                    "/api/auth/login",
                    json={"username": "testuser", "password": "wrong"},
                )
        finally:
            app.dependency_overrides.pop(get_user_repo, None)

        assert res.status_code == 401


# ── /me 엔드포인트 ────────────────────────────────────────────────

class TestMe:
    def _valid_token(self) -> str:
        payload = {
            "sub": "1",
            "user_id": 1,
            "username": "testuser",
            "name": "테스트",
            "role": "EMPLOYEE",
            "exp": datetime.now(timezone.utc) + timedelta(hours=8),
        }
        return jwt.encode(payload, _TEST_SECRET, algorithm=_ALGORITHM)

    def test_me_with_valid_cookie_returns_user(self):
        token = self._valid_token()
        with TestClient(app, raise_server_exceptions=False) as client:
            res = client.get("/api/auth/me", cookies={"access_token": token})
        assert res.status_code == 200
        assert res.json()["username"] == "testuser"

    def test_me_without_cookie_returns_401(self):
        with TestClient(app, raise_server_exceptions=False) as client:
            res = client.get("/api/auth/me")
        assert res.status_code == 401

    def test_me_with_invalid_token_returns_401(self):
        with TestClient(app, raise_server_exceptions=False) as client:
            res = client.get("/api/auth/me", cookies={"access_token": "invalid.token.here"})
        assert res.status_code == 401

    def test_me_with_expired_token_returns_401(self):
        payload = {
            "sub": "1",
            "user_id": 1,
            "username": "testuser",
            "name": "테스트",
            "role": "EMPLOYEE",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = jwt.encode(payload, _TEST_SECRET, algorithm=_ALGORITHM)
        with TestClient(app, raise_server_exceptions=False) as client:
            res = client.get("/api/auth/me", cookies={"access_token": expired_token})
        assert res.status_code == 401


# ── 로그아웃 ─────────────────────────────────────────────────────

class TestLogout:
    def test_logout_returns_message(self):
        with TestClient(app, raise_server_exceptions=False) as client:
            res = client.post("/api/auth/logout")
        assert res.status_code == 200
        assert res.json()["message"] == "로그아웃 완료"

    def test_logout_clears_cookie(self):
        with TestClient(app, raise_server_exceptions=False) as client:
            res = client.post("/api/auth/logout")
        set_cookie = res.headers.get("set-cookie", "")
        assert "access_token" in set_cookie
        assert "max-age=0" in set_cookie.lower()


# ── 보호된 엔드포인트 인증 필요 확인 ──────────────────────────────

class TestProtectedEndpoints:
    def test_customers_without_auth_returns_401(self):
        with TestClient(app, raise_server_exceptions=False) as client:
            res = client.get("/api/customers")
        assert res.status_code == 401

    def test_employees_without_auth_returns_401(self):
        with TestClient(app, raise_server_exceptions=False) as client:
            res = client.get("/api/employees")
        assert res.status_code == 401

    def test_dashboard_without_auth_returns_401(self):
        with TestClient(app, raise_server_exceptions=False) as client:
            res = client.get("/api/dashboard/summary")
        assert res.status_code == 401

    def test_health_endpoint_no_auth_required(self):
        with TestClient(app, raise_server_exceptions=False) as client:
            res = client.get("/api/health")
        assert res.status_code == 200

    def test_auth_login_no_auth_required(self):
        """로그인 엔드포인트는 인증 없이 접근 가능해야 한다."""
        # 존재하지 않는 사용자도 401이지만 인증 오류(401)가 아닌 자격증명 오류(401)
        mock_r = _mock_repo(None)
        app.dependency_overrides[get_user_repo] = lambda: mock_r
        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                res = client.post(
                    "/api/auth/login",
                    json={"username": "x", "password": "y"},
                )
        finally:
            app.dependency_overrides.pop(get_user_repo, None)
        # 422가 아님(스키마 오류), 401임(자격증명 오류)
        assert res.status_code != 422
        assert res.status_code in (200, 401)
