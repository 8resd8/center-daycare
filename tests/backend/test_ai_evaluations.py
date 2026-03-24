"""AI 평가 API 테스트."""

import pytest
from unittest.mock import MagicMock, patch
from contextlib import contextmanager
from datetime import datetime
from .conftest import make_mock_ai_evaluation_repo


@pytest.fixture
def mock_repo(app):
    repo = make_mock_ai_evaluation_repo()
    from backend.dependencies import get_ai_evaluation_repo
    app.dependency_overrides[get_ai_evaluation_repo] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_ai_evaluation_repo, None)


@pytest.fixture
def mock_service(app):
    svc = MagicMock()
    from backend.dependencies import get_evaluation_service
    app.dependency_overrides[get_evaluation_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_evaluation_service, None)


SAMPLE_AI_EVAL = {
    "ai_eval_id": 1,
    "record_id": 100,
    "category": "신체",
    "oer_fidelity": "O",
    "specificity_score": "O",
    "grammar_score": "O",
    "grade_code": "우수",
    "reason_text": "평가 사유",
    "suggestion_text": "수정 제안",
    "original_text": "원본 텍스트",
    "created_at": None,
}


class TestGetAiEvaluations:
    def test_record_id_필수(self, client, mock_repo):
        resp = client.get("/api/ai-evaluations")
        assert resp.status_code == 422

    def test_평가_목록_반환(self, client, mock_repo):
        mock_repo.get_all_evaluations_by_record.return_value = [SAMPLE_AI_EVAL]
        resp = client.get("/api/ai-evaluations?record_id=100")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["ai_eval_id"] == 1
        assert data[0]["grade_code"] == "우수"

    def test_빈_결과(self, client, mock_repo):
        mock_repo.get_all_evaluations_by_record.return_value = []
        resp = client.get("/api/ai-evaluations?record_id=999")
        assert resp.status_code == 200
        assert resp.json() == []


class TestEvaluateRecord:
    PAYLOAD = {
        "record_id": 100,
        "category": "신체",
        "note_text": "식사보조 및 체위변경 도움",
        "writer_user_id": 1,
    }

    def test_AI_평가_실행(self, client, mock_repo, mock_service):
        mock_service.process_daily_note_evaluation.return_value = {
            "grade_code": "우수",
            "reason_text": "충분히 작성됨",
        }
        resp = client.post("/api/ai-evaluations/evaluate", json=self.PAYLOAD)
        assert resp.status_code == 200
        data = resp.json()
        assert data["grade_code"] == "우수"

    def test_AI_평가_파라미터_전달(self, client, mock_repo, mock_service):
        mock_service.process_daily_note_evaluation.return_value = {}
        client.post("/api/ai-evaluations/evaluate", json=self.PAYLOAD)
        mock_service.process_daily_note_evaluation.assert_called_once_with(
            record_id=100,
            category="신체",
            note_text="식사보조 및 체위변경 도움",
            note_writer_user_id=1,
        )


class TestEvaluateFullRecord:
    def _make_mock_db(self, result):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = result

        @contextmanager
        def _mock_db_query():
            yield mock_cursor

        return patch("modules.db_connection.db_query", _mock_db_query)

    def test_기록_없으면_404(self, client, mock_repo, mock_service):
        with self._make_mock_db(None):
            resp = client.post("/api/ai-evaluations/evaluate-record/9999")
        assert resp.status_code == 404

    def test_AI_평가_실패시_500(self, client, mock_repo, mock_service):
        record = {"record_id": 100, "customer_id": 1, "customer_name": "홍길동"}
        mock_service.evaluate_special_note_with_ai.return_value = None
        with self._make_mock_db(record):
            resp = client.post("/api/ai-evaluations/evaluate-record/100")
        assert resp.status_code == 500

    def test_전체_평가_성공(self, client, mock_repo, mock_service):
        record = {"record_id": 100, "customer_id": 1, "customer_name": "홍길동"}
        ai_result = {"grade_code": "우수"}
        mock_service.evaluate_special_note_with_ai.return_value = ai_result
        mock_service.save_special_note_evaluation.return_value = None
        with self._make_mock_db(record):
            resp = client.post("/api/ai-evaluations/evaluate-record/100")
        assert resp.status_code == 200
        assert resp.json()["grade_code"] == "우수"
