"""주간 보고서 API 테스트."""

import pytest
from datetime import date
from unittest.mock import MagicMock, patch
from .conftest import make_mock_weekly_status_repo, make_mock_customer_repo


@pytest.fixture
def mock_weekly_repo(app):
    repo = make_mock_weekly_status_repo()
    from backend.dependencies import get_weekly_status_repo
    app.dependency_overrides[get_weekly_status_repo] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_weekly_status_repo, None)


@pytest.fixture
def mock_report_service(app):
    svc = MagicMock()
    svc.generate_weekly_report.return_value = "주간 보고서 텍스트"
    from backend.dependencies import get_report_service
    app.dependency_overrides[get_report_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_report_service, None)


class TestListWeeklyReports:
    def test_customer_id_필수(self, client, mock_weekly_repo):
        resp = client.get("/api/weekly-reports")
        assert resp.status_code == 422

    def test_빈_결과(self, client, mock_weekly_repo):
        mock_weekly_repo.get_all_by_customer.return_value = []
        resp = client.get("/api/weekly-reports?customer_id=1")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_날짜_범위_없을때_전체_조회(self, client, mock_weekly_repo):
        mock_weekly_repo.get_all_by_customer.return_value = [
            {
                "start_date": date(2024, 1, 1),
                "end_date": date(2024, 1, 7),
                "report_text": "보고서 내용",
            }
        ]
        resp = client.get("/api/weekly-reports?customer_id=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["report_text"] == "보고서 내용"

    def test_날짜_범위_있을때_특정_조회(self, client, mock_weekly_repo):
        mock_weekly_repo.load_weekly_status.return_value = "특정 주 보고서"
        resp = client.get(
            "/api/weekly-reports?customer_id=1&start_date=2024-01-01&end_date=2024-01-07"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["report_text"] == "특정 주 보고서"
        assert data[0]["customer_id"] == 1

    def test_날짜_범위_있지만_보고서_없을때_빈_목록(self, client, mock_weekly_repo):
        mock_weekly_repo.load_weekly_status.return_value = None
        resp = client.get(
            "/api/weekly-reports?customer_id=1&start_date=2024-01-01&end_date=2024-01-07"
        )
        assert resp.status_code == 200
        assert resp.json() == []


class TestGenerateWeeklyReport:
    PAYLOAD = {
        "customer_id": 1,
        "start_date": "2024-01-08",
        "end_date": "2024-01-14",
    }

    def test_AI_보고서_생성(self, client, mock_weekly_repo, mock_report_service):
        from tests.backend.conftest import SAMPLE_CUSTOMER

        with (
            patch("modules.repositories.customer.CustomerRepository") as MockCR,
            patch("modules.weekly_data_analyzer.compute_weekly_status") as mock_compute,
        ):
            MockCR.return_value.get_customer.return_value = SAMPLE_CUSTOMER
            mock_compute.return_value = {"data": "주간 데이터"}
            mock_weekly_repo.load_weekly_status.return_value = None

            resp = client.post("/api/weekly-reports/generate", json=self.PAYLOAD)

        assert resp.status_code == 200
        assert "report_text" in resp.json()

    def test_수급자_없으면_404(self, client, mock_weekly_repo, mock_report_service):
        with patch("modules.repositories.customer.CustomerRepository") as MockCR:
            MockCR.return_value.get_customer.return_value = None
            resp = client.post("/api/weekly-reports/generate", json=self.PAYLOAD)

        assert resp.status_code == 404

    def test_AI_오류시_500(self, client, mock_weekly_repo, mock_report_service):
        from tests.backend.conftest import SAMPLE_CUSTOMER

        mock_report_service.generate_weekly_report.return_value = {"error": "AI 오류"}

        with (
            patch("modules.repositories.customer.CustomerRepository") as MockCR,
            patch("modules.weekly_data_analyzer.compute_weekly_status") as mock_compute,
        ):
            MockCR.return_value.get_customer.return_value = SAMPLE_CUSTOMER
            mock_compute.return_value = {}
            mock_weekly_repo.load_weekly_status.return_value = None

            resp = client.post("/api/weekly-reports/generate", json=self.PAYLOAD)

        assert resp.status_code == 500


class TestSaveWeeklyReport:
    def test_보고서_저장_200(self, client, mock_weekly_repo):
        payload = {
            "customer_id": 1,
            "start_date": "2024-01-08",
            "end_date": "2024-01-14",
            "report_text": "저장할 보고서 내용",
        }
        resp = client.put("/api/weekly-reports/1", json=payload)
        assert resp.status_code == 200
        assert resp.json()["message"] == "저장 완료"
        mock_weekly_repo.save_weekly_status.assert_called_once()
