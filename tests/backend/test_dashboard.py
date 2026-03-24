"""대시보드 API 테스트.

db_query를 직접 사용하는 엔드포인트들을 mock으로 테스트.
"""

import pytest
from unittest.mock import MagicMock, patch
from contextlib import contextmanager


def make_mock_cursor(*fetchall_results):
    """여러 fetchone/fetchall 결과를 순서대로 반환하는 커서."""
    cursor = MagicMock()
    return cursor


@contextmanager
def mock_db_query_ctx(side_effect_list):
    """db_query를 모킹 — fetchone/fetchall을 순서대로 반환."""
    cursor = MagicMock()
    cursor.fetchone.side_effect = side_effect_list
    cursor.fetchall.return_value = []

    @contextmanager
    def _inner():
        yield cursor

    with patch("modules.db_connection.db_query", _inner):
        yield cursor


class TestSummary:
    def test_KPI_요약_반환(self, client):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            {"cnt": 10},   # total_customers
            {"cnt": 5},    # total_employees
            {"cnt": 100},  # total_records
            {"avg_score": 2.5},  # avg_grade_score
        ]

        @contextmanager
        def _mock_db():
            yield cursor

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get("/api/dashboard/summary")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_customers"] == 10
        assert data["total_employees"] == 5
        assert data["total_records"] == 100
        assert data["avg_grade_score"] == 2.5

    def test_날짜_필터_포함_KPI(self, client):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            {"cnt": 3},
            {"cnt": 2},
            {"cnt": 20},
            {"avg_score": None},
        ]

        @contextmanager
        def _mock_db():
            yield cursor

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get("/api/dashboard/summary?start_date=2024-01-01&end_date=2024-01-31")

        assert resp.status_code == 200
        data = resp.json()
        assert data["avg_grade_score"] is None

    def test_avg_score_없을때_None(self, client):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            {"cnt": 0},
            {"cnt": 0},
            {"cnt": 0},
            {"avg_score": None},
        ]

        @contextmanager
        def _mock_db():
            yield cursor

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get("/api/dashboard/summary")

        assert resp.status_code == 200
        assert resp.json()["avg_grade_score"] is None


class TestEvaluationTrend:
    def test_평가_추이_반환(self, client):
        from datetime import date
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {"eval_date": date(2024, 1, 15), "excellent": 3, "average": 2, "improvement": 1},
        ]

        @contextmanager
        def _mock_db():
            yield cursor

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get("/api/dashboard/evaluation-trend")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["date"] == "2024-01-15"
        assert data[0]["excellent"] == 3

    def test_빈_결과(self, client):
        cursor = MagicMock()
        cursor.fetchall.return_value = []

        @contextmanager
        def _mock_db():
            yield cursor

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get("/api/dashboard/evaluation-trend")

        assert resp.status_code == 200
        assert resp.json() == []


class TestEmployeeRankings:
    def test_랭킹_반환(self, client):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {
                "user_id": 1,
                "name": "김요양",
                "total_records": 10,
                "excellent_count": 8,
                "average_count": 1,
                "improvement_count": 1,
            }
        ]

        @contextmanager
        def _mock_db():
            yield cursor

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get("/api/dashboard/employee-rankings")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["user_id"] == 1
        assert "score" in data[0]
        assert data[0]["score"] > 0

    def test_평가없는_직원_score_0(self, client):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {
                "user_id": 2,
                "name": "박간호",
                "total_records": 0,
                "excellent_count": 0,
                "average_count": 0,
                "improvement_count": 0,
            }
        ]

        @contextmanager
        def _mock_db():
            yield cursor

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get("/api/dashboard/employee-rankings")

        assert resp.json()[0]["score"] == 0.0


class TestAiGradeDist:
    def test_등급_분포(self, client):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {"grade": "우수", "count": 10},
            {"grade": "평균", "count": 5},
            {"grade": "개선", "count": 2},
        ]

        @contextmanager
        def _mock_db():
            yield cursor

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get("/api/dashboard/ai-grade-dist")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        grades = {d["grade"] for d in data}
        assert "우수" in grades


class TestEmployeeDetails:
    def test_직원_없으면_404(self, client):
        cursor = MagicMock()
        cursor.fetchone.return_value = None

        @contextmanager
        def _mock_db():
            yield cursor

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get("/api/dashboard/employee/9999/details")

        assert resp.status_code == 404

    def test_직원_상세_반환(self, client):
        from datetime import date
        call_count = 0

        class FakeCursor:
            def execute(self, q, p=None):
                pass

            def fetchone(self):
                return {"user_id": 1, "name": "김요양"}

            def fetchall(self):
                return [
                    {
                        "record_id": 100,
                        "date": date(2024, 1, 15),
                        "customer_id": 1,
                        "customer_name": "홍길동",
                        "grade_code": "우수",
                        "category": "신체",
                        "suggestion_text": "잘 작성됨",
                    }
                ]

        fake_cursor = FakeCursor()

        @contextmanager
        def _mock_db():
            yield fake_cursor

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get("/api/dashboard/employee/1/details")

        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == 1
        assert data["name"] == "김요양"
        assert isinstance(data["records"], list)


class TestEmpEvalTrend:
    def test_직원평가_추이(self, client):
        from datetime import date
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {
                "eval_date": date(2024, 1, 15),
                "cnt_누락": 2,
                "cnt_내용부족": 1,
                "cnt_오타": 0,
                "cnt_문법": 0,
                "cnt_오류": 1,
            }
        ]

        @contextmanager
        def _mock_db():
            yield cursor

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get("/api/dashboard/emp-eval-trend")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["누락"] == 2
        assert data[0]["date"] == "2024-01-15"


class TestEmpEvalCategory:
    def test_카테고리별_건수(self, client):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {"category": "신체", "count": 5},
            {"category": "인지", "count": 3},
        ]

        @contextmanager
        def _mock_db():
            yield cursor

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get("/api/dashboard/emp-eval-category")

        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["category"] == "신체"
        assert data[0]["count"] == 5


class TestEmpEvalRankings:
    def test_지적건수_랭킹(self, client):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {
                "user_id": 1,
                "name": "김요양",
                "total_count": 5,
                "cnt_누락": 3,
                "cnt_내용부족": 1,
                "cnt_오타": 1,
                "cnt_문법": 0,
                "cnt_오류": 0,
            }
        ]

        @contextmanager
        def _mock_db():
            yield cursor

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get("/api/dashboard/emp-eval-rankings")

        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["total_count"] == 5
        assert data[0]["main_type"] == "누락"

    def test_지적없는_직원_main_type_대시(self, client):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {
                "user_id": 2,
                "name": "박재활",
                "total_count": 0,
                "cnt_누락": 0,
                "cnt_내용부족": 0,
                "cnt_오타": 0,
                "cnt_문법": 0,
                "cnt_오류": 0,
            }
        ]

        @contextmanager
        def _mock_db():
            yield cursor

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get("/api/dashboard/emp-eval-rankings")

        assert resp.json()[0]["main_type"] == "-"


class TestEmployeeEvalHistory:
    def test_직원_없으면_404(self, client):
        cursor = MagicMock()
        cursor.fetchone.return_value = None

        @contextmanager
        def _mock_db():
            yield cursor

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get("/api/dashboard/employee/9999/emp-eval-history")

        assert resp.status_code == 404

    def test_지적_이력_반환(self, client):
        from datetime import date

        class FakeCursor:
            def execute(self, q, p=None):
                pass

            def fetchone(self):
                return {"user_id": 1, "name": "김요양"}

            def fetchall(self):
                return [
                    {
                        "emp_eval_id": 1,
                        "evaluation_date": date(2024, 1, 15),
                        "target_date": date(2024, 1, 10),
                        "category": "신체",
                        "evaluation_type": "누락",
                        "comment": "테스트",
                        "score": 1,
                    }
                ]

        @contextmanager
        def _mock_db():
            yield FakeCursor()

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get("/api/dashboard/employee/1/emp-eval-history")

        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == 1
        assert len(data["records"]) == 1
        assert data["records"][0]["evaluation_type"] == "누락"
