"""주간 보고서 API 테스트."""

import pytest
from datetime import date
from unittest.mock import MagicMock, patch, call
from .conftest import make_mock_weekly_status_repo, make_mock_customer_repo, SAMPLE_CUSTOMER


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
            patch("backend.routers.weekly_reports.compute_weekly_status") as mock_compute,
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
        mock_report_service.generate_weekly_report.return_value = {"error": "AI 오류"}

        with (
            patch("modules.repositories.customer.CustomerRepository") as MockCR,
            patch("backend.routers.weekly_reports.compute_weekly_status") as mock_compute,
        ):
            MockCR.return_value.get_customer.return_value = SAMPLE_CUSTOMER
            mock_compute.return_value = {}
            mock_weekly_repo.load_weekly_status.return_value = None

            resp = client.post("/api/weekly-reports/generate", json=self.PAYLOAD)

        assert resp.status_code == 500

    def test_응답에_weekly_table_포함(self, client, mock_weekly_repo, mock_report_service):
        """generate 응답에 weekly_table이 포함되어야 한다."""
        with (
            patch("modules.repositories.customer.CustomerRepository") as MockCR,
            patch("backend.routers.weekly_reports.compute_weekly_status") as mock_compute,
        ):
            MockCR.return_value.get_customer.return_value = SAMPLE_CUSTOMER
            mock_compute.return_value = {
                "scores": {},
                "trend": {
                    "weekly_table": [{"주간": "지난주"}, {"주간": "이번주"}],
                    "ai_payload": {},
                },
            }
            mock_weekly_repo.load_weekly_status.return_value = None
            resp = client.post("/api/weekly-reports/generate", json=self.PAYLOAD)

        assert resp.status_code == 200
        data = resp.json()
        assert "weekly_table" in data
        assert len(data["weekly_table"]) == 2

    def test_응답에_scores_포함(self, client, mock_weekly_repo, mock_report_service):
        """generate 응답에 scores가 포함되어야 한다."""
        with (
            patch("modules.repositories.customer.CustomerRepository") as MockCR,
            patch("backend.routers.weekly_reports.compute_weekly_status") as mock_compute,
        ):
            MockCR.return_value.get_customer.return_value = SAMPLE_CUSTOMER
            mock_compute.return_value = {
                "scores": {"physical": {"label": "신체활동", "prev": 55.0, "curr": 60.0}},
                "trend": {"weekly_table": [], "ai_payload": {}},
            }
            mock_weekly_repo.load_weekly_status.return_value = None
            resp = client.post("/api/weekly-reports/generate", json=self.PAYLOAD)

        assert resp.status_code == 200
        data = resp.json()
        assert "scores" in data
        assert "physical" in data["scores"]

    def test_ai_payload_경로_올바름(self, client, mock_weekly_repo, mock_report_service):
        """회귀 테스트: trend.ai_payload가 서비스에 전달되어야 함 (전체 analysis_result 아님)."""
        expected_payload = {"current_week": {"physical": "테스트 신체"}}
        with (
            patch("modules.repositories.customer.CustomerRepository") as MockCR,
            patch("backend.routers.weekly_reports.compute_weekly_status") as mock_compute,
        ):
            MockCR.return_value.get_customer.return_value = SAMPLE_CUSTOMER
            mock_compute.return_value = {
                "scores": {},
                "trend": {
                    "weekly_table": [],
                    "ai_payload": expected_payload,
                },
            }
            mock_weekly_repo.load_weekly_status.return_value = None
            resp = client.post("/api/weekly-reports/generate", json=self.PAYLOAD)

        assert resp.status_code == 200
        call_kwargs = mock_report_service.generate_weekly_report.call_args
        # analysis_payload 인자로 전달된 값 확인 (analysis_result 전체가 아닌 ai_payload여야 함)
        passed = call_kwargs.kwargs.get("analysis_payload") or call_kwargs.args[2]
        assert "current_week" in passed, "ai_payload.current_week이 서비스에 전달되지 않음"

    def test_trend_없을때_빈_weekly_table(self, client, mock_weekly_repo, mock_report_service):
        """analysis_result에 trend 없으면 weekly_table=[] (KeyError 아님)."""
        with (
            patch("modules.repositories.customer.CustomerRepository") as MockCR,
            patch("backend.routers.weekly_reports.compute_weekly_status") as mock_compute,
        ):
            MockCR.return_value.get_customer.return_value = SAMPLE_CUSTOMER
            mock_compute.return_value = {"scores": {}}  # trend 키 없음
            mock_weekly_repo.load_weekly_status.return_value = None
            resp = client.post("/api/weekly-reports/generate", json=self.PAYLOAD)

        assert resp.status_code == 200
        assert resp.json()["weekly_table"] == []


class TestGetWeeklyAnalysis:
    BASE = "/api/weekly-reports/analysis"

    def test_customer_id_필수(self, client):
        resp = client.get(f"{self.BASE}?start_date=2024-01-08&end_date=2024-01-14")
        assert resp.status_code == 422

    def test_start_date_필수(self, client):
        resp = client.get(f"{self.BASE}?customer_id=1&end_date=2024-01-14")
        assert resp.status_code == 422

    def test_end_date_필수(self, client):
        resp = client.get(f"{self.BASE}?customer_id=1&start_date=2024-01-08")
        assert resp.status_code == 422

    def test_수급자_없으면_404(self, client):
        with patch("modules.repositories.customer.CustomerRepository") as MockCR:
            MockCR.return_value.get_customer.return_value = None
            resp = client.get(
                f"{self.BASE}?customer_id=999&start_date=2024-01-08&end_date=2024-01-14"
            )
        assert resp.status_code == 404

    def test_분석_성공_필드_포함(self, client):
        """정상 응답에 필수 필드가 모두 포함되어야 한다."""
        with (
            patch("modules.repositories.customer.CustomerRepository") as MockCR,
            patch("backend.routers.weekly_reports.compute_weekly_status") as mock_compute,
        ):
            MockCR.return_value.get_customer.return_value = SAMPLE_CUSTOMER
            mock_compute.return_value = {
                "ranges": (
                    (date(2024, 1, 1), date(2024, 1, 7)),
                    (date(2024, 1, 8), date(2024, 1, 14)),
                ),
                "scores": {"physical": {"label": "신체활동", "prev": 55.0, "curr": 60.0}},
                "trend": {
                    "weekly_table": [{"주간": "지난주"}, {"주간": "이번주"}],
                    "prev_prog_entries": [],
                    "curr_prog_entries": [{"date": "01-08", "detail": "미니골프"}],
                },
            }
            resp = client.get(
                f"{self.BASE}?customer_id=1&start_date=2024-01-08&end_date=2024-01-14"
            )

        assert resp.status_code == 200
        data = resp.json()
        for key in ["weekly_table", "scores", "prev_range", "curr_range", "prev_prog_entries", "curr_prog_entries"]:
            assert key in data, f"'{key}' 필드가 응답에 없음"

    def test_범위_날짜_형식_문자열(self, client):
        """prev_range, curr_range가 ['YYYY-MM-DD', 'YYYY-MM-DD'] 형식이어야 한다."""
        with (
            patch("modules.repositories.customer.CustomerRepository") as MockCR,
            patch("backend.routers.weekly_reports.compute_weekly_status") as mock_compute,
        ):
            MockCR.return_value.get_customer.return_value = SAMPLE_CUSTOMER
            mock_compute.return_value = {
                "ranges": (
                    (date(2024, 1, 1), date(2024, 1, 7)),
                    (date(2024, 1, 8), date(2024, 1, 14)),
                ),
                "scores": {},
                "trend": {"weekly_table": [], "prev_prog_entries": [], "curr_prog_entries": []},
            }
            resp = client.get(
                f"{self.BASE}?customer_id=1&start_date=2024-01-08&end_date=2024-01-14"
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["prev_range"] == ["2024-01-01", "2024-01-07"]
        assert data["curr_range"] == ["2024-01-08", "2024-01-14"]

    def test_레코드_없을때_빈배열_not_error(self, client):
        """데이터 없어도 KeyError/500이 아닌 빈 배열 반환."""
        with (
            patch("modules.repositories.customer.CustomerRepository") as MockCR,
            patch("backend.routers.weekly_reports.compute_weekly_status") as mock_compute,
        ):
            MockCR.return_value.get_customer.return_value = SAMPLE_CUSTOMER
            mock_compute.return_value = {
                "data": [],
                "ranges": (
                    (date(2024, 1, 1), date(2024, 1, 7)),
                    (date(2024, 1, 8), date(2024, 1, 14)),
                ),
                "scores": {},
                # trend 키 없음 → no-data 경로
            }
            resp = client.get(
                f"{self.BASE}?customer_id=1&start_date=2024-01-08&end_date=2024-01-14"
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["weekly_table"] == []
        assert data["curr_prog_entries"] == []

    def test_trend_없을때_빈배열_반환(self, client):
        """analysis_result에 trend 키 없을 때 빈 배열 (500 아님)."""
        with (
            patch("modules.repositories.customer.CustomerRepository") as MockCR,
            patch("backend.routers.weekly_reports.compute_weekly_status") as mock_compute,
        ):
            MockCR.return_value.get_customer.return_value = SAMPLE_CUSTOMER
            mock_compute.return_value = {"scores": {}, "ranges": None}
            resp = client.get(
                f"{self.BASE}?customer_id=1&start_date=2024-01-08&end_date=2024-01-14"
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["weekly_table"] == []
        assert data["prev_prog_entries"] == []
        assert data["curr_prog_entries"] == []

    def test_ranges_없을때_null_반환(self, client):
        """ranges가 None이면 prev_range, curr_range가 null (unpack 예외 아님)."""
        with (
            patch("modules.repositories.customer.CustomerRepository") as MockCR,
            patch("backend.routers.weekly_reports.compute_weekly_status") as mock_compute,
        ):
            MockCR.return_value.get_customer.return_value = SAMPLE_CUSTOMER
            mock_compute.return_value = {"scores": {}, "ranges": None}
            resp = client.get(
                f"{self.BASE}?customer_id=1&start_date=2024-01-08&end_date=2024-01-14"
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["prev_range"] is None
        assert data["curr_range"] is None

    def test_prog_entries_데이터_있을때_포함(self, client):
        """curr_prog_entries에 이번주 활동 데이터가 올바르게 포함되어야 한다."""
        with (
            patch("modules.repositories.customer.CustomerRepository") as MockCR,
            patch("backend.routers.weekly_reports.compute_weekly_status") as mock_compute,
        ):
            MockCR.return_value.get_customer.return_value = SAMPLE_CUSTOMER
            mock_compute.return_value = {
                "scores": {},
                "ranges": (
                    (date(2024, 1, 1), date(2024, 1, 7)),
                    (date(2024, 1, 8), date(2024, 1, 14)),
                ),
                "trend": {
                    "weekly_table": [],
                    "prev_prog_entries": [],
                    "curr_prog_entries": [{"date": "01-08", "detail": "미니골프 활동"}],
                },
            }
            resp = client.get(
                f"{self.BASE}?customer_id=1&start_date=2024-01-08&end_date=2024-01-14"
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["curr_prog_entries"]) == 1
        assert data["curr_prog_entries"][0]["detail"] == "미니골프 활동"

    def test_prev_prog_entries_지난주_분리(self, client):
        """prev_prog_entries와 curr_prog_entries가 주차별로 각각 분리되어야 한다."""
        with (
            patch("modules.repositories.customer.CustomerRepository") as MockCR,
            patch("backend.routers.weekly_reports.compute_weekly_status") as mock_compute,
        ):
            MockCR.return_value.get_customer.return_value = SAMPLE_CUSTOMER
            mock_compute.return_value = {
                "scores": {},
                "ranges": (
                    (date(2024, 1, 1), date(2024, 1, 7)),
                    (date(2024, 1, 8), date(2024, 1, 14)),
                ),
                "trend": {
                    "weekly_table": [],
                    "prev_prog_entries": [{"date": "01-03", "detail": "지난주 활동"}],
                    "curr_prog_entries": [{"date": "01-08", "detail": "이번주 활동"}],
                },
            }
            resp = client.get(
                f"{self.BASE}?customer_id=1&start_date=2024-01-08&end_date=2024-01-14"
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["prev_prog_entries"]) == 1
        assert data["prev_prog_entries"][0]["detail"] == "지난주 활동"
        assert len(data["curr_prog_entries"]) == 1
        assert data["curr_prog_entries"][0]["detail"] == "이번주 활동"


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
