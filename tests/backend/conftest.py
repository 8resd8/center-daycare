"""FastAPI 백엔드 테스트 공통 픽스처."""

import pytest
from datetime import date
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def app():
    """FastAPI 앱 인스턴스 (라이프사이클 없이)."""
    import sys
    import os
    from pathlib import Path

    root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(root))

    # DB 연결 풀 초기화 없이 앱 가져오기
    with patch("modules.db_connection._get_connection_pool", return_value=MagicMock()):
        from backend.main import app as _app
        yield _app


@pytest.fixture
def client(app):
    """TestClient 인스턴스."""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ─── 공통 Mock Repo 팩토리 ──────────────────────────────────────────────

def make_mock_customer_repo():
    repo = MagicMock()
    repo.list_customers.return_value = []
    repo.get_customer.return_value = None
    repo.create_customer.return_value = 1
    repo.update_customer.return_value = 1
    repo.delete_customer.return_value = 1
    return repo


def make_mock_employee_repo():
    repo = MagicMock()
    repo.list_users.return_value = []
    repo.get_user.return_value = None
    repo.create_user.return_value = 1
    repo.update_user.return_value = 1
    repo.soft_delete_user.return_value = 1
    return repo


def make_mock_daily_info_repo():
    repo = MagicMock()
    repo.get_customer_records.return_value = []
    repo.get_customers_with_records.return_value = []
    repo.delete_daily_record.return_value = 1
    repo.save_parsed_data.return_value = 0
    return repo


def make_mock_weekly_status_repo():
    repo = MagicMock()
    repo.load_weekly_status.return_value = None
    repo.get_all_by_customer.return_value = []
    repo.save_weekly_status.return_value = None
    return repo


def make_mock_ai_evaluation_repo():
    repo = MagicMock()
    repo.get_all_evaluations_by_record.return_value = []
    return repo


def make_mock_employee_evaluation_repo():
    repo = MagicMock()
    repo.get_all_users.return_value = []
    repo.get_evaluations_by_record.return_value = []
    repo.find_existing_evaluation.return_value = None
    repo.save_evaluation.return_value = 1
    repo.update_evaluation.return_value = 1
    repo.delete_evaluation.return_value = 1
    return repo


# ─── 표준 샘플 데이터 ──────────────────────────────────────────────────

SAMPLE_CUSTOMER = {
    "customer_id": 1,
    "name": "홍길동",
    "birth_date": date(1950, 1, 1),
    "gender": "남",
    "recognition_no": "L1234567890",
    "benefit_start_date": date(2024, 1, 1),
    "grade": "3등급",
}

SAMPLE_EMPLOYEE = {
    "user_id": 1,
    "name": "김요양",
    "gender": "여",
    "birth_date": date(1990, 5, 1),
    "work_status": "재직",
    "job_type": "요양보호사",
    "hire_date": date(2022, 3, 1),
    "resignation_date": None,
    "license_name": "요양보호사",
    "license_date": date(2021, 6, 1),
}

SAMPLE_EMPLOYEE_EVALUATION = {
    "emp_eval_id": 1,
    "record_id": 100,
    "target_user_id": 1,
    "category": "신체",
    "evaluation_type": "누락",
    "evaluation_date": date(2024, 1, 15),
    "target_date": date(2024, 1, 10),
    "evaluator_user_id": 2,
    "score": 1,
    "comment": "테스트 코멘트",
    "target_user_name": "김요양",
    "evaluator_user_name": "박관리자",
}

SAMPLE_DAILY_RECORD = {
    "record_id": 100,
    "customer_id": 1,
    "date": date(2024, 1, 15),
    "total_service_time": "08:00",
    "physical_note": "신체 특이사항",
    "writer_physical": "김요양",
    "meal_breakfast": "죽",
    "meal_lunch": "일반식",
    "meal_dinner": "일반식",
    "toilet_care": "기저귀",
    "bath_time": "10:00",
    "bp_temp": "120/80, 36.5",
    "prog_therapy": "물리치료",
    "cognitive_note": "인지 특이사항",
    "writer_cognitive": "김요양",
    "nursing_note": "간호 특이사항",
    "writer_nursing": "이간호",
    "functional_note": "기능 특이사항",
    "writer_recovery": "박재활",
}
