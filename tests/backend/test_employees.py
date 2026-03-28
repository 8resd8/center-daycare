"""직원 CRUD API 테스트.

어제 발생 이슈 방지:
- 404 처리 (존재하지 않는 직원)
- 201 응답 시 user_id 포함 여부
- 퇴사 처리(soft delete) 동작 확인
"""

import pytest
from unittest.mock import MagicMock, patch
from .conftest import make_mock_employee_repo, SAMPLE_EMPLOYEE


@pytest.fixture
def mock_repo(app):
    repo = make_mock_employee_repo()
    from backend.dependencies import get_user_repo
    app.dependency_overrides[get_user_repo] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_user_repo, None)


class TestListEmployees:
    def test_빈_목록_반환(self, client, mock_repo):
        resp = client.get("/api/employees")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_직원_목록_반환(self, client, mock_repo):
        mock_repo.list_users.return_value = [SAMPLE_EMPLOYEE]
        resp = client.get("/api/employees")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["user_id"] == 1

    def test_필터_파라미터_전달(self, client, mock_repo):
        mock_repo.list_users.return_value = []
        client.get("/api/employees?keyword=김&work_status=재직")
        mock_repo.list_users.assert_called_once_with(keyword="김", work_status="재직")


class TestGetEmployee:
    def test_존재하는_직원_조회(self, client, mock_repo):
        mock_repo.get_user.return_value = SAMPLE_EMPLOYEE
        resp = client.get("/api/employees/1")
        assert resp.status_code == 200
        assert resp.json()["name"] == "김요양"

    def test_존재하지_않는_직원_404(self, client, mock_repo):
        mock_repo.get_user.return_value = None
        resp = client.get("/api/employees/9999")
        assert resp.status_code == 404


class TestCreateEmployee:
    def test_직원_생성_201(self, client, mock_repo):
        mock_repo.create_user.return_value = 1
        mock_repo.get_user.return_value = SAMPLE_EMPLOYEE

        payload = {
            "name": "김요양",
            "username": "user01",
            "password": "pass1234",
            "gender": "여",
            "birth_date": "1990-05-01",
            "work_status": "재직",
            "job_type": "요양보호사",
            "hire_date": "2022-03-01",
        }
        resp = client.post("/api/employees", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "user_id" in data
        assert data["name"] == "김요양"

    def test_비밀번호_해시_처리_확인(self, client, mock_repo):
        """원본 비밀번호가 그대로 저장되면 안 됨."""
        mock_repo.create_user.return_value = 1
        mock_repo.get_user.return_value = SAMPLE_EMPLOYEE

        payload = {
            "name": "테스트",
            "username": "user02",
            "password": "plaintext",
        }
        client.post("/api/employees", json=payload)
        call_kwargs = mock_repo.create_user.call_args.kwargs
        hashed = call_kwargs["password"]
        # 해시된 비밀번호 = 평문과 달라야 함
        assert hashed != "plaintext"
        # bcrypt 해시 형식 확인 ($2b$ 접두사)
        assert hashed.startswith("$2b$")


class TestUpdateEmployee:
    def test_직원_수정_200(self, client, mock_repo):
        updated = {**SAMPLE_EMPLOYEE, "job_type": "사회복지사"}
        mock_repo.get_user.return_value = updated
        payload = {"name": "김요양", "job_type": "사회복지사"}
        resp = client.put("/api/employees/1", json=payload)
        assert resp.status_code == 200
        assert resp.json()["job_type"] == "사회복지사"

    def test_존재하지_않는_직원_수정_404(self, client, mock_repo):
        mock_repo.get_user.return_value = None
        resp = client.put("/api/employees/9999", json={"name": "없음"})
        assert resp.status_code == 404


class TestDeleteEmployee:
    def test_퇴사_처리_204(self, client, mock_repo):
        mock_repo.soft_delete_user.return_value = 1
        resp = client.delete("/api/employees/1")
        assert resp.status_code == 204
        mock_repo.soft_delete_user.assert_called_once_with(1)

    def test_존재하지_않는_직원_퇴사_404(self, client, mock_repo):
        mock_repo.soft_delete_user.return_value = 0
        resp = client.delete("/api/employees/9999")
        assert resp.status_code == 404


# ── 마스킹 테스트 ────────────────────────────────────────────────────


class TestEmployeeMasking:
    """VIEWER가 직원 조회 시 PII 마스킹 검증."""

    @pytest.fixture
    def mock_repo_for_viewer(self, app):
        repo = make_mock_employee_repo()
        from backend.dependencies import get_user_repo
        app.dependency_overrides[get_user_repo] = lambda: repo
        yield repo
        app.dependency_overrides.pop(get_user_repo, None)

    def test_viewer_목록_조회시_이름_마스킹(self, viewer_client, mock_repo_for_viewer):
        mock_repo_for_viewer.list_users.return_value = [SAMPLE_EMPLOYEE]
        resp = viewer_client.get("/api/employees")
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["name"] == "김**"
        assert data[0]["hire_date"] == "****-**-**"

    def test_viewer_개별_조회시_마스킹(self, viewer_client, mock_repo_for_viewer):
        mock_repo_for_viewer.get_user.return_value = SAMPLE_EMPLOYEE
        resp = viewer_client.get("/api/employees/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "김**"
        assert data["job_type"] == "***"
