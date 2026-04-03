"""FastAPI 백엔드 테스트 공통 픽스처."""

import pytest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from jose import jwt


# ─── 앱 / TestClient ────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def app():
    """FastAPI 앱 인스턴스 (DB 연결 풀 초기화 없이)."""
    import sys
    from pathlib import Path

    root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(root))

    with patch("modules.db_connection._get_connection_pool", return_value=MagicMock()):
        from backend.main import app as _app

        yield _app


@pytest.fixture
def client(app):
    """인증 우회 TestClient (get_current_user 오버라이드 포함)."""
    from backend.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": 1,
        "username": "admin",
        "name": "관리자",
        "role": "ADMIN",
    }
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def viewer_client(app):
    """VIEWER 역할 TestClient (RBAC 테스트용)."""
    from backend.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": 99,
        "username": "viewer",
        "name": "열람자",
        "role": "VIEWER",
    }
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def unauth_client(app):
    """인증 오버라이드 없는 TestClient (401 테스트용)."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ─── JWT / 쿠키 헬퍼 ────────────────────────────────────────────────────

_TEST_SECRET = "test-secret-key-for-testing"
_ALGORITHM = "HS256"


def _make_token(
    user_id: int = 1,
    username: str = "admin",
    name: str = "관리자",
    role: str = "ADMIN",
) -> str:
    payload = {
        "sub": str(user_id),
        "user_id": user_id,
        "username": username,
        "name": name,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=8),
    }
    return jwt.encode(payload, _TEST_SECRET, algorithm=_ALGORITHM)


def _make_refresh_token(
    user_id: int = 1,
    token_type: str = "refresh",
    expire_delta: timedelta | None = None,
) -> str:
    """테스트용 리프레시 토큰 생성."""
    payload = {
        "sub": str(user_id),
        "user_id": user_id,
        "type": token_type,
        "exp": datetime.now(timezone.utc) + (expire_delta or timedelta(days=7)),
    }
    return jwt.encode(payload, _TEST_SECRET, algorithm=_ALGORITHM)


@pytest.fixture
def auth_cookies():
    """유효한 JWT 쿠키 딕셔너리 반환."""
    return {"access_token": _make_token()}


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
    repo.get_evaluation_by_id.return_value = None
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

# ── 피드백 리포트 ────────────────────────────────────────────────────────

SAMPLE_FEEDBACK_REPORT = {
    "report_id": 1,
    "user_id": 1,
    "target_month": "2026-01",
    "admin_note": None,
    "ai_result": {
        "summary_table": [
            {"구분": "오류", "상세내용": "이동 도움 기재 오류 2회", "비고": "총 2건"},
            {"구분": "누락", "상세내용": "인지 특이사항 미작성 5회", "비고": "총 5건"},
            {"구분": "횟수부족", "상세내용": "내용 단순 기재 3회", "비고": "총 3건"},
            {"구분": "좋았던 부분", "상세내용": "신체활동 꾸준히 작성", "비고": ""},
            {
                "구분": "개선해야 하는 부분",
                "상세내용": "어르신 반응 없이 행위만 기재",
                "비고": "",
            },
            {
                "구분": "개선방법",
                "상세내용": "프로그램명+반응+도움 순으로 작성",
                "비고": "",
            },
        ],
        "improvement_examples": [
            {
                "기존_작성방식": "인지 프로그램 도움 드림",
                "개선_작성방식": "퍼즐 맞추기 실시, 3개 완성하심",
            },
        ],
    },
    "created_at": "2026-01-31T10:00:00",
    "updated_at": "2026-01-31T10:00:00",
}


def make_mock_feedback_service():
    svc = MagicMock()
    svc.generate_and_save.return_value = SAMPLE_FEEDBACK_REPORT
    svc.list_months.return_value = [
        {"report_id": 1, "target_month": "2026-01", "created_at": "2026-01-31T10:00:00"}
    ]
    svc.get_by_month.return_value = SAMPLE_FEEDBACK_REPORT
    return svc
