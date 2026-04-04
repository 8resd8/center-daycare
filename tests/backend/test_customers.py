"""수급자 CRUD API 테스트.

어제 발생 이슈 방지:
- 404 처리 (존재하지 않는 수급자)
- 201 응답 시 customer_id 포함 여부
- response 스키마 필드 누락 방지
"""

import pytest
from unittest.mock import patch, MagicMock
from .conftest import make_mock_customer_repo, SAMPLE_CUSTOMER


@pytest.fixture
def mock_repo(app):
    repo = make_mock_customer_repo()
    from backend.dependencies import get_customer_repo

    app.dependency_overrides[get_customer_repo] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_customer_repo, None)


class TestListCustomers:
    def test_빈_목록_반환(self, client, mock_repo):
        mock_repo.list_customers.return_value = []
        resp = client.get("/api/customers")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_수급자_목록_반환(self, client, mock_repo):
        mock_repo.list_customers.return_value = [SAMPLE_CUSTOMER]
        resp = client.get("/api/customers")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["customer_id"] == 1
        assert data[0]["name"] == "홍길동"

    def test_키워드_검색_전달(self, client, mock_repo):
        mock_repo.list_customers.return_value = []
        client.get("/api/customers?keyword=홍")
        mock_repo.list_customers.assert_called_once_with(keyword="홍")

    def test_키워드_없을때_None_전달(self, client, mock_repo):
        mock_repo.list_customers.return_value = []
        client.get("/api/customers")
        mock_repo.list_customers.assert_called_once_with(keyword=None)


class TestGetCustomer:
    def test_존재하는_수급자_조회(self, client, mock_repo):
        mock_repo.get_customer.return_value = SAMPLE_CUSTOMER
        resp = client.get("/api/customers/1")
        assert resp.status_code == 200
        assert resp.json()["customer_id"] == 1

    def test_존재하지_않는_수급자_404(self, client, mock_repo):
        mock_repo.get_customer.return_value = None
        resp = client.get("/api/customers/9999")
        assert resp.status_code == 404
        assert "찾을 수 없습니다" in resp.json()["detail"]


class TestCreateCustomer:
    def test_수급자_생성_201(self, client, mock_repo):
        mock_repo.create_customer.return_value = 1
        mock_repo.get_customer.return_value = SAMPLE_CUSTOMER

        payload = {
            "name": "홍길동",
            "birth_date": "1950-01-01",
            "gender": "남",
            "recognition_no": "L1234567890",
            "benefit_start_date": "2024-01-01",
            "grade": "3등급",
        }
        resp = client.post("/api/customers", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        # 응답 스키마 필드 검증
        assert "customer_id" in data
        assert data["name"] == "홍길동"

    def test_수급자_생성_repo_호출_확인(self, client, mock_repo):
        mock_repo.create_customer.return_value = 2
        mock_repo.get_customer.return_value = {**SAMPLE_CUSTOMER, "customer_id": 2}

        payload = {"name": "이순신", "gender": "남"}
        client.post("/api/customers", json=payload)
        mock_repo.create_customer.assert_called_once()
        args = mock_repo.create_customer.call_args
        assert args.kwargs["name"] == "이순신"


class TestUpdateCustomer:
    def test_수급자_수정_200(self, client, mock_repo):
        mock_repo.get_customer.return_value = {**SAMPLE_CUSTOMER, "grade": "2등급"}
        payload = {
            "name": "홍길동",
            "grade": "2등급",
        }
        resp = client.put("/api/customers/1", json=payload)
        assert resp.status_code == 200
        assert resp.json()["grade"] == "2등급"

    def test_존재하지_않는_수급자_수정_404(self, client, mock_repo):
        mock_repo.get_customer.return_value = None
        payload = {"name": "없는사람"}
        resp = client.put("/api/customers/9999", json=payload)
        assert resp.status_code == 404


class TestDeleteCustomer:
    def test_수급자_삭제_204(self, client, mock_repo):
        mock_repo.delete_customer.return_value = 1
        resp = client.delete("/api/customers/1")
        assert resp.status_code == 204

    def test_존재하지_않는_수급자_삭제_404(self, client, mock_repo):
        mock_repo.delete_customer.return_value = 0
        resp = client.delete("/api/customers/9999")
        assert resp.status_code == 404


# ── 마스킹 테스트 ────────────────────────────────────────────────────


class TestCustomerMasking:
    """VIEWER가 수급자 조회 시 PII 마스킹 검증."""

    @pytest.fixture
    def mock_repo_for_viewer(self, app):
        repo = make_mock_customer_repo()
        from backend.dependencies import get_customer_repo

        app.dependency_overrides[get_customer_repo] = lambda: repo
        yield repo
        app.dependency_overrides.pop(get_customer_repo, None)

    def test_viewer_목록_조회시_이름_마스킹(self, viewer_client, mock_repo_for_viewer):
        mock_repo_for_viewer.list_customers.return_value = [SAMPLE_CUSTOMER]
        with patch("backend.routers.customers._audit_repo", return_value=MagicMock()):
            resp = viewer_client.get("/api/customers")
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["name"] == "홍**"
        assert data[0]["grade"] == "**"

    def test_admin_목록_조회시_원본_반환(self, client, mock_repo_for_viewer):
        mock_repo_for_viewer.list_customers.return_value = [SAMPLE_CUSTOMER]
        resp = client.get("/api/customers")
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["name"] == "홍길동"
        assert data[0]["grade"] == "3등급"


# ── 입력 유효성 검사 ─────────────────────────────────────────────────


class TestCustomerValidation:
    """수급자 생성 요청 유효성 검사 — 422 반환 케이스."""

    def test_name_필수_422(self, client, mock_repo):
        """name 없이 POST → 422."""
        resp = client.post("/api/customers", json={"gender": "남"})
        assert resp.status_code == 422

    def test_잘못된_benefit_start_date_422(self, client, mock_repo):
        """benefit_start_date에 날짜 형식이 아닌 값 → 422."""
        resp = client.post(
            "/api/customers",
            json={"name": "홍길동", "benefit_start_date": "not-a-date"},
        )
        assert resp.status_code == 422
