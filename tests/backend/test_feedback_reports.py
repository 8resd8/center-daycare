"""직원 피드백 리포트 API 테스트."""

import pytest
from unittest.mock import patch, MagicMock
from contextlib import contextmanager
from .conftest import make_mock_feedback_service


@pytest.fixture
def mock_service(app):
    svc = make_mock_feedback_service()
    from backend.dependencies import get_feedback_service

    app.dependency_overrides[get_feedback_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_feedback_service, None)


def _mock_db_with_user(user_row, eval_rows=None):
    """user_row: 직원 조회 결과, eval_rows: 평가 이력"""

    @contextmanager
    def _db(dictionary=True):
        cursor = MagicMock()
        # fetchone: 첫 번째 호출은 user, 두 번째도 user(목록 엔드포인트)
        cursor.fetchone.return_value = user_row
        cursor.fetchall.return_value = eval_rows or []
        yield cursor

    return _db


# ── POST: 생성 ───────────────────────────────────────────────────────────


class TestCreateFeedbackReport:
    PAYLOAD = {"target_month": "2026-01", "admin_note": None}

    def test_생성_성공_200(self, client, mock_service):
        mock_db = _mock_db_with_user(
            {"user_id": 1, "name": "enc_name"},
            [
                {
                    "evaluation_date": "2026-01-10",
                    "target_date": "2026-01-08",
                    "category": "신체",
                    "evaluation_type": "누락",
                    "comment": "테스트",
                }
            ],
        )
        with patch("backend.routers.feedback_reports.db_query", mock_db):
            with patch("backend.routers.feedback_reports.EncryptionService") as MockEnc:
                MockEnc.return_value.safe_decrypt.return_value = "홍길동"
                resp = client.post(
                    "/api/dashboard/employee/1/feedback-report", json=self.PAYLOAD
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["report_id"] == 1
        assert data["target_month"] == "2026-01"
        assert "ai_result" in data
        assert "summary_table" in data["ai_result"]

    def test_존재하지_않는_직원_404(self, client, mock_service):
        mock_db = _mock_db_with_user(None)
        with patch("backend.routers.feedback_reports.db_query", mock_db):
            resp = client.post(
                "/api/dashboard/employee/999/feedback-report", json=self.PAYLOAD
            )
        assert resp.status_code == 404

    def test_AI_파싱_오류_500(self, client, mock_service):
        mock_service.generate_and_save.side_effect = ValueError(
            "AI 응답 JSON 파싱 오류"
        )
        mock_db = _mock_db_with_user({"user_id": 1, "name": "enc_name"})
        with patch("backend.routers.feedback_reports.db_query", mock_db):
            with patch("backend.routers.feedback_reports.EncryptionService") as MockEnc:
                MockEnc.return_value.safe_decrypt.return_value = "홍길동"
                resp = client.post(
                    "/api/dashboard/employee/1/feedback-report", json=self.PAYLOAD
                )
        assert resp.status_code == 500

    def test_비ADMIN_403(self, viewer_client, mock_service):
        resp = viewer_client.post(
            "/api/dashboard/employee/1/feedback-report", json=self.PAYLOAD
        )
        assert resp.status_code == 403


# ── GET: 목록 ────────────────────────────────────────────────────────────


class TestListFeedbackMonths:
    def test_목록_반환(self, client, mock_service):
        mock_db = _mock_db_with_user({"user_id": 1})
        with patch("backend.routers.feedback_reports.db_query", mock_db):
            resp = client.get("/api/dashboard/employee/1/feedback-reports")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["target_month"] == "2026-01"

    def test_존재하지_않는_직원_404(self, client, mock_service):
        mock_db = _mock_db_with_user(None)
        with patch("backend.routers.feedback_reports.db_query", mock_db):
            resp = client.get("/api/dashboard/employee/999/feedback-reports")
        assert resp.status_code == 404

    def test_비ADMIN_403(self, viewer_client, mock_service):
        resp = viewer_client.get("/api/dashboard/employee/1/feedback-reports")
        assert resp.status_code == 403


# ── GET: 단건 ────────────────────────────────────────────────────────────


class TestGetFeedbackReport:
    def test_단건_조회(self, client, mock_service):
        resp = client.get("/api/dashboard/employee/1/feedback-report/2026-01")
        assert resp.status_code == 200
        data = resp.json()
        assert data["report_id"] == 1
        assert data["target_month"] == "2026-01"

    def test_없는_월_404(self, client, mock_service):
        mock_service.get_by_month.return_value = None
        resp = client.get("/api/dashboard/employee/1/feedback-report/2025-01")
        assert resp.status_code == 404

    def test_비ADMIN_403(self, viewer_client, mock_service):
        resp = viewer_client.get("/api/dashboard/employee/1/feedback-report/2026-01")
        assert resp.status_code == 403
