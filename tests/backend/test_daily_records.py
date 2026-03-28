"""일일 기록 API 테스트."""

import pytest
from unittest.mock import patch, MagicMock
from contextlib import contextmanager
from datetime import date
from .conftest import make_mock_daily_info_repo, SAMPLE_DAILY_RECORD


@pytest.fixture
def mock_repo(app):
    repo = make_mock_daily_info_repo()
    from backend.dependencies import get_daily_info_repo
    app.dependency_overrides[get_daily_info_repo] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_daily_info_repo, None)


class TestListDailyRecords:
    def test_customer_id_필수(self, client, mock_repo):
        resp = client.get("/api/daily-records")
        assert resp.status_code == 400
        assert "customer_id" in resp.json()["detail"]

    def test_customer_id_제공시_목록_반환(self, client, mock_repo):
        mock_repo.get_customer_records.return_value = [SAMPLE_DAILY_RECORD]
        resp = client.get("/api/daily-records?customer_id=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["record_id"] == 100

    def test_날짜_범위_필터(self, client, mock_repo):
        mock_repo.get_customer_records.return_value = []
        client.get("/api/daily-records?customer_id=1&start_date=2024-01-01&end_date=2024-01-31")
        mock_repo.get_customer_records.assert_called_once_with(
            customer_id=1,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

    def test_빈_목록(self, client, mock_repo):
        mock_repo.get_customer_records.return_value = []
        resp = client.get("/api/daily-records?customer_id=999")
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetCustomersWithRecords:
    def test_기록_있는_수급자_목록(self, client, mock_repo):
        mock_repo.get_customers_with_records.return_value = [
            {
                "customer_id": 1,
                "name": "홍길동",
                "birth_date": date(1950, 1, 1),
                "grade": "3등급",
                "recognition_no": "L123",
                "record_count": 5,
                "first_date": date(2024, 1, 1),
                "last_date": date(2024, 1, 31),
            }
        ]
        resp = client.get("/api/daily-records/customers-with-records")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["customer_id"] == 1
        assert data[0]["record_count"] == 5

    def test_날짜_필터_전달(self, client, mock_repo):
        mock_repo.get_customers_with_records.return_value = []
        client.get("/api/daily-records/customers-with-records?start_date=2024-01-01&end_date=2024-01-31")
        mock_repo.get_customers_with_records.assert_called_once_with(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )


class TestGetDailyRecord:
    def _make_mock_db(self, result):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = result

        @contextmanager
        def _mock_db_query():
            yield mock_cursor

        return patch("modules.db_connection.db_query", _mock_db_query)

    def test_기록_조회(self, client, mock_repo):
        record = {**SAMPLE_DAILY_RECORD, "record_id": 100, "customer_id": 1, "date": date(2024, 1, 15)}
        with self._make_mock_db(record):
            resp = client.get("/api/daily-records/100")
        assert resp.status_code == 200
        assert resp.json()["record_id"] == 100

    def test_존재하지_않는_기록_404(self, client, mock_repo):
        with self._make_mock_db(None):
            resp = client.get("/api/daily-records/9999")
        assert resp.status_code == 404


class TestDeleteDailyRecord:
    def test_삭제_204(self, client, mock_repo):
        resp = client.delete("/api/daily-records/100")
        assert resp.status_code == 204
        mock_repo.delete_daily_record.assert_called_once_with(100)


# ── 마스킹 테스트 ────────────────────────────────────────────────────


class TestDailyRecordsMasking:
    """VIEWER가 customers-with-records 조회 시 PII 마스킹 검증."""

    @pytest.fixture
    def mock_repo_for_viewer(self, app):
        repo = make_mock_daily_info_repo()
        from backend.dependencies import get_daily_info_repo
        app.dependency_overrides[get_daily_info_repo] = lambda: repo
        yield repo
        app.dependency_overrides.pop(get_daily_info_repo, None)

    def test_viewer_조회시_이름_마스킹(self, viewer_client, mock_repo_for_viewer):
        mock_repo_for_viewer.get_customers_with_records.return_value = [
            {
                "customer_id": 1,
                "name": "홍길동",
                "birth_date": date(1950, 1, 1),
                "grade": "3등급",
                "recognition_no": "L123",
                "record_count": 5,
                "first_date": date(2024, 1, 1),
                "last_date": date(2024, 1, 31),
            }
        ]
        resp = viewer_client.get("/api/daily-records/customers-with-records")
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["name"] == "홍**"
        assert data[0]["grade"] == "**"
