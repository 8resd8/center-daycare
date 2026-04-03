"""FeedbackReportRepository SQL 파라미터 바인딩 테스트.

핵심 회귀: DATE_FORMAT('%Y-%m-%dT%H:%i:%s') 내부의 %s를 MySQL connector가
파라미터 플레이스홀더로 오인하는 버그 방지.
재현 조건: DATE_FORMAT 포맷 문자에 %s(초)가 있으면 ProgrammingError 발생.
해결: %s → %S (MySQL 초 포맷 대소문자 무관, connector는 %s만 파라미터로 인식)
"""

import json
import re
import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from modules.repositories.feedback_report import FeedbackReportRepository

# 실제 mysql.connector의 RE_PY_PARAM = re.compile(b"(%s)") 와 동일: 소문자 %s 전부 매치
RE_MYSQL_PARAM = re.compile(r"%s")


def _count_placeholders(query: str) -> int:
    """MySQL connector가 파라미터 슬롯으로 인식하는 %s 개수."""
    return len(RE_MYSQL_PARAM.findall(query))


@pytest.fixture
def repo():
    return FeedbackReportRepository()


@pytest.fixture
def mock_cursor():
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    cursor.fetchone.return_value = None
    cursor.lastrowid = 1
    cursor.rowcount = 1
    return cursor


@pytest.fixture
def mock_db_ctx(mock_cursor):
    """modules.repositories.base의 db_query / db_transaction을 교체."""

    @contextmanager
    def _query(dictionary=True):
        yield mock_cursor

    @contextmanager
    def _transaction(dictionary=False):
        yield mock_cursor

    with (
        patch("modules.repositories.base.db_query", _query),
        patch("modules.repositories.base.db_transaction", _transaction),
    ):
        yield mock_cursor


# ── 회귀 테스트: DATE_FORMAT %s 이스케이프 ───────────────────────────────


class TestDateFormatEscape:
    """DATE_FORMAT 포맷 문자열 내 %s가 파라미터 슬롯으로 오인되지 않는지 검증."""

    def test_list_months_파라미터_슬롯_일치(self, repo, mock_db_ctx):
        """`list_months`: DATE_FORMAT 내 %s가 %%s로 이스케이프되어 슬롯 수 = 1."""
        repo.list_months(user_id=1)

        query, params = mock_db_ctx.execute.call_args.args
        placeholders = _count_placeholders(query)
        assert placeholders == len(params), (
            f"DATE_FORMAT 내 %s가 파라미터로 오인됨: "
            f"쿼리 슬롯 {placeholders}개, 파라미터 {len(params)}개. "
            "초 포맷은 %%s 대신 %%S 사용 필요 (MySQL %S = seconds, connector는 %s만 파라미터로 인식)."
        )

    def test_get_by_month_파라미터_슬롯_일치(self, repo, mock_db_ctx):
        """`get_by_month`: created_at + updated_at 두 DATE_FORMAT의 %s 이스케이프."""
        repo.get_by_month(user_id=1, target_month="2026-01")

        query, params = mock_db_ctx.execute.call_args.args
        placeholders = _count_placeholders(query)
        assert placeholders == len(params), (
            f"DATE_FORMAT 내 %s가 이스케이프되지 않음: "
            f"쿼리 슬롯 {placeholders}개, 파라미터 {len(params)}개."
        )


# ── 기능 테스트 ──────────────────────────────────────────────────────────


class TestListMonths:
    def test_결과_dict_목록_반환(self, repo, mock_db_ctx):
        mock_db_ctx.fetchall.return_value = [
            {
                "report_id": 1,
                "target_month": "2026-01",
                "created_at": "2026-01-31T10:00:00",
            },
            {
                "report_id": 2,
                "target_month": "2025-12",
                "created_at": "2025-12-31T10:00:00",
            },
        ]
        result = repo.list_months(user_id=1)
        assert len(result) == 2
        assert result[0]["target_month"] == "2026-01"

    def test_빈_결과_빈_목록(self, repo, mock_db_ctx):
        mock_db_ctx.fetchall.return_value = []
        result = repo.list_months(user_id=99)
        assert result == []

    def test_user_id_파라미터_전달(self, repo, mock_db_ctx):
        repo.list_months(user_id=42)
        _, params = mock_db_ctx.execute.call_args.args
        assert 42 in params


class TestGetByMonth:
    def test_존재하는_리포트_반환(self, repo, mock_db_ctx):
        mock_db_ctx.fetchone.return_value = {
            "report_id": 1,
            "user_id": 1,
            "target_month": "2026-01",
            "admin_note": None,
            "ai_result": json.dumps({"summary_table": []}),
            "created_at": "2026-01-31T10:00:00",
            "updated_at": "2026-01-31T10:00:00",
        }
        result = repo.get_by_month(user_id=1, target_month="2026-01")
        assert result is not None
        assert result["target_month"] == "2026-01"
        assert isinstance(result["ai_result"], dict)

    def test_ai_result_JSON_문자열을_dict로_변환(self, repo, mock_db_ctx):
        mock_db_ctx.fetchone.return_value = {
            "report_id": 1,
            "user_id": 1,
            "target_month": "2026-01",
            "admin_note": None,
            "ai_result": '{"summary_table": [{"구분": "오류"}]}',
            "created_at": "2026-01-31T10:00:00",
            "updated_at": "2026-01-31T10:00:00",
        }
        result = repo.get_by_month(user_id=1, target_month="2026-01")
        assert isinstance(result["ai_result"], dict)
        assert result["ai_result"]["summary_table"][0]["구분"] == "오류"

    def test_없는_월_None_반환(self, repo, mock_db_ctx):
        mock_db_ctx.fetchone.return_value = None
        result = repo.get_by_month(user_id=1, target_month="2020-01")
        assert result is None

    def test_user_id와_target_month_파라미터_전달(self, repo, mock_db_ctx):
        repo.get_by_month(user_id=7, target_month="2026-03")
        _, params = mock_db_ctx.execute.call_args.args
        assert 7 in params
        assert "2026-03" in params


class TestUpsert:
    def test_insert_성공_report_id_반환(self, repo, mock_db_ctx):
        mock_db_ctx.lastrowid = 5
        ai_result = {"summary_table": []}
        result = repo.upsert(
            user_id=1,
            target_month="2026-01",
            admin_note=None,
            ai_result=ai_result,
        )
        assert result == 5

    def test_ai_result_JSON_직렬화_후_전달(self, repo, mock_db_ctx):
        ai_result = {"summary_table": [{"구분": "누락"}]}
        repo.upsert(
            user_id=1, target_month="2026-01", admin_note=None, ai_result=ai_result
        )

        _, params = mock_db_ctx.execute.call_args.args
        # 4번째 파라미터가 JSON 문자열이어야 함
        json_param = params[3]
        assert isinstance(json_param, str)
        parsed = json.loads(json_param)
        assert parsed["summary_table"][0]["구분"] == "누락"

    def test_파라미터_슬롯_일치(self, repo, mock_db_ctx):
        repo.upsert(user_id=1, target_month="2026-01", admin_note=None, ai_result={})
        query, params = mock_db_ctx.execute.call_args.args
        assert _count_placeholders(query) == len(params)
