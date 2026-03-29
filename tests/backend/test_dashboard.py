"""대시보드 API 테스트.

db_query를 직접 사용하는 엔드포인트들을 mock으로 테스트.
"""

import pytest
from datetime import date
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
        # 새 구현: 1차 fetchall(유저 목록) + 유저별 fetchone(레코드 통계)
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {"user_id": 1, "name": "김요양"}
        ]
        cursor.fetchone.return_value = {
            "total_records": 10,
            "excellent_count": 8,
            "average_count": 1,
            "improvement_count": 1,
        }

        @contextmanager
        def _mock_db():
            yield cursor

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get("/api/dashboard/employee-rankings")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["user_id"] == 1
        assert data[0]["name"] == "김요양"
        assert "score" in data[0]
        assert data[0]["score"] > 0

    def test_평가없는_직원_score_0(self, client):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {"user_id": 2, "name": "박간호"}
        ]
        cursor.fetchone.return_value = {
            "total_records": 0,
            "excellent_count": 0,
            "average_count": 0,
            "improvement_count": 0,
        }

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


# ── 마스킹 테스트 ────────────────────────────────────────────────────


class TestEmployeeRankingsMasking:
    """비ADMIN 사용자의 employee-rankings 이름 마스킹 검증."""

    def test_viewer_이름_마스킹(self, viewer_client):
        mock_enc = MagicMock()
        mock_enc.return_value.safe_decrypt.return_value = "김요양"

        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {"user_id": 1, "name": "encrypted_name"}
        ]
        cursor.fetchone.return_value = {
            "total_records": 5,
            "excellent_count": 3,
            "average_count": 1,
            "improvement_count": 1,
        }

        @contextmanager
        def _mock_db():
            yield cursor

        with (
            patch("modules.db_connection.db_query", _mock_db),
            patch("backend.routers.dashboard.EncryptionService", mock_enc),
        ):
            resp = viewer_client.get("/api/dashboard/employee-rankings")

        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["name"] == "김**"

    def test_admin_이름_원본(self, client):
        mock_enc = MagicMock()
        mock_enc.return_value.safe_decrypt.return_value = "김요양"

        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {"user_id": 1, "name": "encrypted_name"}
        ]
        cursor.fetchone.return_value = {
            "total_records": 5,
            "excellent_count": 3,
            "average_count": 1,
            "improvement_count": 1,
        }

        @contextmanager
        def _mock_db():
            yield cursor

        with (
            patch("modules.db_connection.db_query", _mock_db),
            patch("backend.routers.dashboard.EncryptionService", mock_enc),
        ):
            resp = client.get("/api/dashboard/employee-rankings")

        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["name"] == "김요양"


class TestEmpEvalRankingsMasking:
    """비ADMIN 사용자의 emp-eval-rankings 이름 마스킹 검증."""

    def test_viewer_이름_마스킹(self, viewer_client):
        mock_enc = MagicMock()
        mock_enc.return_value.safe_decrypt.return_value = "김요양"

        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {
                "user_id": 1,
                "name": "encrypted_name",
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

        with (
            patch("modules.db_connection.db_query", _mock_db),
            patch("backend.routers.dashboard.EncryptionService", mock_enc),
        ):
            resp = viewer_client.get("/api/dashboard/emp-eval-rankings")

        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["name"] == "김**"

    def test_admin_이름_원본(self, client):
        mock_enc = MagicMock()
        mock_enc.return_value.safe_decrypt.return_value = "김요양"

        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {
                "user_id": 1,
                "name": "encrypted_name",
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

        with (
            patch("modules.db_connection.db_query", _mock_db),
            patch("backend.routers.dashboard.EncryptionService", mock_enc),
        ):
            resp = client.get("/api/dashboard/emp-eval-rankings")

        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["name"] == "김요양"


# ── 기간 비교 테스트 ─────────────────────────────────────────────


class TestPeriodComparison:
    def test_기간_비교_데이터_반환(self, client):
        cursor = MagicMock()
        # 현재 기간 fetchall → 이전 기간 fetchall
        cursor.fetchall.side_effect = [
            [{"evaluation_type": "누락", "cnt": 10}, {"evaluation_type": "오타", "cnt": 5}],
            [{"evaluation_type": "누락", "cnt": 7}, {"evaluation_type": "오타", "cnt": 3}],
        ]

        @contextmanager
        def _mock_db():
            yield cursor

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get(
                "/api/dashboard/period-comparison?start_date=2024-01-15&end_date=2024-01-31"
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["current_period"]["total"] == 15
        assert data["previous_period"]["total"] == 10
        assert data["change_rate"] == 50.0
        assert "누락" in data["current_period"]["by_type"]

    def test_날짜_없으면_빈_데이터(self, client):
        resp = client.get("/api/dashboard/period-comparison")
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_period"]["total"] == 0
        assert data["previous_period"]["total"] == 0
        assert data["change_rate"] is None

    def test_이전기간_0건이면_change_rate_null(self, client):
        cursor = MagicMock()
        cursor.fetchall.side_effect = [
            [{"evaluation_type": "누락", "cnt": 5}],  # 현재
            [],  # 이전: 0건
        ]

        @contextmanager
        def _mock_db():
            yield cursor

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get(
                "/api/dashboard/period-comparison?start_date=2024-01-15&end_date=2024-01-31"
            )

        data = resp.json()
        assert data["change_rate"] is None
        assert data["current_period"]["total"] == 5


# ── KPI 요약 테스트 ──────────────────────────────────────────────


class TestKpiSummary:
    def test_KPI_delta_포함_반환(self, client):
        cursor = MagicMock()
        # 순서: total_employees → curr_total → curr_high_risk → curr_emp_cnt
        #                        → prev_total → prev_high_risk → prev_emp_cnt
        cursor.fetchone.side_effect = [
            {"cnt": 14},    # total_employees
            {"total": 45},  # curr total
            {"cnt": 3},     # curr high_risk
            {"emp_cnt": 10},  # curr distinct employees
            {"total": 30},  # prev total
            {"cnt": 2},     # prev high_risk
            {"emp_cnt": 8},   # prev distinct employees
        ]

        @contextmanager
        def _mock_db():
            yield cursor

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get(
                "/api/dashboard/kpi-summary?start_date=2024-01-15&end_date=2024-01-31"
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_issues"] == 45
        assert data["total_issues_prev"] == 30
        assert data["total_issues_delta"] == 50.0
        assert data["high_risk_count"] == 3
        assert data["total_employees"] == 14
        assert data["avg_per_employee"] == 4.5

    def test_이전기간_0건_delta_null(self, client):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            {"cnt": 10},    # total_employees
            {"total": 5},   # curr total
            {"cnt": 0},     # curr high_risk
            {"emp_cnt": 3},   # curr distinct employees
            {"total": 0},   # prev total
            {"cnt": 0},     # prev high_risk
            {"emp_cnt": 0},   # prev distinct employees
        ]

        @contextmanager
        def _mock_db():
            yield cursor

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get(
                "/api/dashboard/kpi-summary?start_date=2024-01-15&end_date=2024-01-31"
            )

        data = resp.json()
        assert data["total_issues_delta"] is None
        assert data["avg_per_employee_delta"] is None

    def test_날짜_필터_미적용시_prev_0(self, client):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            {"cnt": 10},    # total_employees
            {"total": 20},  # curr total (전체)
            {"cnt": 1},     # curr high_risk
            {"emp_cnt": 5},   # curr distinct employees
        ]

        @contextmanager
        def _mock_db():
            yield cursor

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get("/api/dashboard/kpi-summary")

        data = resp.json()
        assert data["total_issues"] == 20
        assert data["total_issues_prev"] == 0
        assert data["total_issues_delta"] is None


# ── 직원별 월별 추이 테스트 ──────────────────────────────────────


class TestEmployeeMonthlyTrend:
    def test_월별_추이_반환(self, client):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            {"user_id": 1},  # user exists
        ]
        cursor.fetchall.return_value = [
            {"month": "2024-01", "count": 3},
            {"month": "2024-02", "count": 5},
        ]

        @contextmanager
        def _mock_db():
            yield cursor

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get("/api/dashboard/employee/1/monthly-trend")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["month"] == "2024-01"
        assert data[1]["count"] == 5

    def test_직원_없으면_404(self, client):
        cursor = MagicMock()
        cursor.fetchone.return_value = None

        @contextmanager
        def _mock_db():
            yield cursor

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get("/api/dashboard/employee/9999/monthly-trend")

        assert resp.status_code == 404

    def test_months_파라미터(self, client):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [{"user_id": 1}]
        cursor.fetchall.return_value = [
            {"month": "2024-01", "count": 2},
        ]

        @contextmanager
        def _mock_db():
            yield cursor

        with patch("modules.db_connection.db_query", _mock_db):
            resp = client.get("/api/dashboard/employee/1/monthly-trend?months=3")

        assert resp.status_code == 200
        # months 파라미터가 SQL에 전달되었는지 확인
        call_args = cursor.execute.call_args_list
        # 두 번째 execute 호출 (첫 번째는 user 존재 확인)
        assert len(call_args) >= 2
        second_call_params = call_args[1][0][1]  # (query, params)의 params
        assert second_call_params == (1, 3)
