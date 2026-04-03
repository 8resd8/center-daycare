# 직원 피드백 리포트 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 직원의 월별 지적 이력을 기반으로 AI 피드백을 생성·저장·조회하는 기능 구현

**Architecture:** Router(`feedback_reports.py`) → `FeedbackService` → `FeedbackReportRepository`. AI 호출은 서비스에서 `get_ai_client().chat_completion()` 사용. DB는 `employee_feedback_reports` 테이블(UNIQUE KEY: user_id+target_month)으로 같은 월 재생성 시 upsert 처리.

**Tech Stack:** FastAPI, Pydantic v2, mysql.connector, React 18 + TanStack Query v5, TypeScript

---

## 파일맵

| 파일 | 작업 |
|------|------|
| `scripts/alter_columns.sql` | `employee_feedback_reports` DDL 추가 |
| `modules/repositories/feedback_report.py` | 신규 — upsert / get_by_month / list_months |
| `modules/clients/feedback_prompt.py` | 신규 — system/user 프롬프트 빌더 |
| `modules/services/feedback_service.py` | 신규 — AI 호출 + 저장 로직 |
| `backend/schemas/feedback_reports.py` | 신규 — Pydantic 스키마 |
| `backend/routers/feedback_reports.py` | 신규 — 엔드포인트 3개 |
| `backend/dependencies.py` | get_feedback_report_repo / get_feedback_service 추가 |
| `backend/main.py` | feedback_reports 라우터 등록 |
| `tests/backend/conftest.py` | mock factory 2개 추가 |
| `tests/backend/test_feedback_reports.py` | 신규 — 라우터 테스트 |
| `frontend/src/types/index.ts` | FeedbackReport 관련 타입 추가 |
| `frontend/src/api/feedbackReports.ts` | 신규 — API 호출 함수 |
| `frontend/src/pages/DashboardPage.tsx` | DetailsTab 서브탭 추가 |

---

## Task 1: DB 테이블 DDL 추가

**Files:**
- Modify: `scripts/alter_columns.sql`

- [ ] **Step 1: DDL 추가**

`scripts/alter_columns.sql` 파일 끝에 다음을 추가:

```sql
-- 직원 피드백 리포트 (AI 생성, 월별 upsert)
CREATE TABLE IF NOT EXISTS employee_feedback_reports (
  report_id    BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id      INT NOT NULL,
  target_month VARCHAR(7) NOT NULL,
  admin_note   TEXT,
  ai_result    JSON NOT NULL,
  created_at   DATETIME DEFAULT NOW(),
  updated_at   DATETIME DEFAULT NOW() ON UPDATE NOW(),
  UNIQUE KEY uq_user_month (user_id, target_month),
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

- [ ] **Step 2: 커밋**

```bash
git add scripts/alter_columns.sql
git commit -m "feat: employee_feedback_reports 테이블 DDL 추가"
```

---

## Task 2: Repository TDD

**Files:**
- Create: `modules/repositories/feedback_report.py`
- Test: via `tests/backend/test_feedback_reports.py` (Task 5에서 통합 테스트)

> Repository는 간단한 DB 래퍼이므로, 라우터 통합 테스트(Task 5)에서 mock으로 검증한다.

- [ ] **Step 1: Repository 구현**

`modules/repositories/feedback_report.py` 를 생성:

```python
"""직원 피드백 리포트 Repository"""

import json
from typing import Optional, List, Dict
from .base import BaseRepository


class FeedbackReportRepository(BaseRepository):

    def upsert(
        self,
        user_id: int,
        target_month: str,
        admin_note: Optional[str],
        ai_result: dict,
    ) -> int:
        """INSERT … ON DUPLICATE KEY UPDATE → report_id 반환"""
        query = """
            INSERT INTO employee_feedback_reports (user_id, target_month, admin_note, ai_result)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                admin_note = VALUES(admin_note),
                ai_result  = VALUES(ai_result),
                report_id  = LAST_INSERT_ID(report_id)
        """
        return self._execute_transaction_lastrowid(
            query,
            (user_id, target_month, admin_note, json.dumps(ai_result, ensure_ascii=False)),
        )

    def get_by_month(self, user_id: int, target_month: str) -> Optional[Dict]:
        """특정 월 리포트 반환. ai_result는 dict로 변환."""
        row = self._execute_query_one(
            "SELECT report_id, user_id, target_month, admin_note, ai_result, "
            "DATE_FORMAT(created_at, '%Y-%m-%dT%H:%i:%s') AS created_at, "
            "DATE_FORMAT(updated_at, '%Y-%m-%dT%H:%i:%s') AS updated_at "
            "FROM employee_feedback_reports "
            "WHERE user_id = %s AND target_month = %s",
            (user_id, target_month),
        )
        if row is None:
            return None
        row = dict(row)
        if isinstance(row.get("ai_result"), str):
            row["ai_result"] = json.loads(row["ai_result"])
        return row

    def list_months(self, user_id: int) -> List[Dict]:
        """저장된 월 목록 (최신순)."""
        rows = self._execute_query(
            "SELECT report_id, target_month, "
            "DATE_FORMAT(created_at, '%Y-%m-%dT%H:%i:%s') AS created_at "
            "FROM employee_feedback_reports "
            "WHERE user_id = %s "
            "ORDER BY target_month DESC",
            (user_id,),
        )
        return [dict(r) for r in rows]
```

- [ ] **Step 2: 커밋**

```bash
git add modules/repositories/feedback_report.py
git commit -m "feat: FeedbackReportRepository — upsert/get_by_month/list_months"
```

---

## Task 3: Prompt Builder

**Files:**
- Create: `modules/clients/feedback_prompt.py`

- [ ] **Step 1: 프롬프트 모듈 생성**

`modules/clients/feedback_prompt.py` 를 생성:

```python
"""직원 피드백 리포트 AI 프롬프트 빌더"""

from typing import Optional, List, Dict

FEEDBACK_SYSTEM_PROMPT = """<role>
  당신은 요양보호사 케어 기록 작성 전문 코치입니다.
  직원의 월별 지적 이력을 분석하여 구체적이고 실용적인 피드백 리포트를 작성합니다.
</role>

<output_format>
  반드시 JSON 형식으로만 응답하세요. 설명 텍스트 없이 JSON만 출력합니다.
  {
    "summary_table": [
      {"구분": "오류",               "상세내용": "...", "비고": "총 N건"},
      {"구분": "누락",               "상세내용": "...", "비고": "총 N건"},
      {"구분": "횟수부족",           "상세내용": "...", "비고": "총 N건"},
      {"구분": "좋았던 부분",        "상세내용": "...", "비고": ""},
      {"구분": "개선해야 하는 부분", "상세내용": "...", "비고": ""},
      {"구분": "개선방법",           "상세내용": "...", "비고": ""}
    ],
    "improvement_examples": [
      {"기존_작성방식": "...", "개선_작성방식": "..."}
    ]
  }
</output_format>"""


def build_user_prompt(
    employee_name: str,
    target_month: str,
    admin_note: Optional[str],
    evaluations: List[Dict],
) -> str:
    """동적 user 프롬프트 빌드."""
    note_block = ""
    if admin_note:
        note_block = f"\n<admin_note>\n  {admin_note}\n</admin_note>"

    records_xml = ""
    for ev in evaluations:
        eval_date = ev.get("evaluation_date", "")
        target_date = ev.get("target_date", "")
        category = ev.get("category", "")
        eval_type = ev.get("evaluation_type", "")
        comment = ev.get("comment", "") or ""
        records_xml += (
            f"\n  <record>"
            f"\n    <evaluation_date>{eval_date}</evaluation_date>"
            f"\n    <target_date>{target_date}</target_date>"
            f"\n    <category>{category}</category>"
            f"\n    <evaluation_type>{eval_type}</evaluation_type>"
            f"\n    <comment>{comment}</comment>"
            f"\n  </record>"
        )

    return (
        f"<target>\n  <name>{employee_name}</name>\n  <month>{target_month}</month>\n</target>"
        f"{note_block}"
        f"\n<evaluation_history count=\"{len(evaluations)}\">"
        f"{records_xml}"
        f"\n</evaluation_history>"
        f"\n<instruction>"
        f"\n  위 지적 이력을 분석하여 직원이 더 나은 케어 기록을 작성할 수 있도록"
        f"\n  구체적이고 실용적인 피드백 리포트를 JSON으로 작성하세요."
        f"\n</instruction>"
    )
```

- [ ] **Step 2: 커밋**

```bash
git add modules/clients/feedback_prompt.py
git commit -m "feat: feedback_prompt — system/user 프롬프트 빌더"
```

---

## Task 4: Service

**Files:**
- Create: `modules/services/feedback_service.py`

- [ ] **Step 1: 서비스 구현**

`modules/services/feedback_service.py` 를 생성:

```python
"""직원 피드백 리포트 서비스 — AI 호출 + DB 저장"""

import json
from typing import Optional, List, Dict

from modules.repositories.feedback_report import FeedbackReportRepository
from modules.clients.ai_client import get_ai_client
from modules.clients.feedback_prompt import FEEDBACK_SYSTEM_PROMPT, build_user_prompt


class FeedbackService:
    def __init__(self, repo: FeedbackReportRepository):
        self.repo = repo

    def generate_and_save(
        self,
        user_id: int,
        employee_name: str,
        target_month: str,
        admin_note: Optional[str],
        evaluations: List[Dict],
    ) -> Dict:
        """AI 피드백 생성 → upsert → 저장된 레코드 반환."""
        user_prompt = build_user_prompt(employee_name, target_month, admin_note, evaluations)
        messages = [
            {"role": "system", "content": FEEDBACK_SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ]
        response = get_ai_client().chat_completion(
            model="gemini-2.5-flash-preview-04-17",
            messages=messages,
        )
        content = response.choices[0].message.content
        try:
            ai_result = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"AI 응답 JSON 파싱 오류: {e}") from e

        self.repo.upsert(user_id, target_month, admin_note, ai_result)
        return self.repo.get_by_month(user_id, target_month)

    def list_months(self, user_id: int) -> List[Dict]:
        return self.repo.list_months(user_id)

    def get_by_month(self, user_id: int, target_month: str) -> Optional[Dict]:
        return self.repo.get_by_month(user_id, target_month)
```

- [ ] **Step 2: 커밋**

```bash
git add modules/services/feedback_service.py
git commit -m "feat: FeedbackService — AI 호출 + upsert 로직"
```

---

## Task 5: Schema + Router + 등록 + 테스트

**Files:**
- Create: `backend/schemas/feedback_reports.py`
- Create: `backend/routers/feedback_reports.py`
- Modify: `backend/dependencies.py`
- Modify: `backend/main.py`
- Modify: `tests/backend/conftest.py`
- Create: `tests/backend/test_feedback_reports.py`

### Step 1: 테스트 fixtures 추가 (conftest.py 수정)

- [ ] **Step 1a: tests/backend/conftest.py 에 mock factory 2개 추가**

`tests/backend/conftest.py` 끝에 추가:

```python
# ── SAMPLE 상수 ─────────────────────────────────────────────────────────

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
            {"구분": "개선해야 하는 부분", "상세내용": "어르신 반응 없이 행위만 기재", "비고": ""},
            {"구분": "개선방법", "상세내용": "프로그램명+반응+도움 순으로 작성", "비고": ""},
        ],
        "improvement_examples": [
            {"기존_작성방식": "인지 프로그램 도움 드림", "개선_작성방식": "퍼즐 맞추기 실시, 3개 완성하심"},
        ],
    },
    "created_at": "2026-01-31T10:00:00",
    "updated_at": "2026-01-31T10:00:00",
}


def make_mock_feedback_report_repo():
    repo = MagicMock()
    repo.upsert.return_value = 1
    repo.get_by_month.return_value = SAMPLE_FEEDBACK_REPORT
    repo.list_months.return_value = [
        {"report_id": 1, "target_month": "2026-01", "created_at": "2026-01-31T10:00:00"}
    ]
    return repo


def make_mock_feedback_service():
    svc = MagicMock()
    svc.repo = make_mock_feedback_report_repo()
    svc.generate_and_save.return_value = SAMPLE_FEEDBACK_REPORT
    svc.list_months.return_value = [
        {"report_id": 1, "target_month": "2026-01", "created_at": "2026-01-31T10:00:00"}
    ]
    svc.get_by_month.return_value = SAMPLE_FEEDBACK_REPORT
    return svc
```

### Step 2: Schema + Router 구현 전 테스트 작성

- [ ] **Step 2a: 테스트 파일 작성 (failing)**

`tests/backend/test_feedback_reports.py` 를 생성:

```python
"""직원 피드백 리포트 API 테스트."""

import pytest
from .conftest import make_mock_feedback_service, SAMPLE_FEEDBACK_REPORT


@pytest.fixture
def mock_service(app):
    svc = make_mock_feedback_service()
    from backend.dependencies import get_feedback_service
    app.dependency_overrides[get_feedback_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_feedback_service, None)


# ── POST: 생성 ───────────────────────────────────────────────────────────

class TestCreateFeedbackReport:
    PAYLOAD = {"target_month": "2026-01", "admin_note": None}

    def test_생성_성공_200(self, client, mock_service):
        """POST 성공 시 200 + FeedbackReportResponse 반환."""
        # user 조회 mock
        from unittest.mock import patch, MagicMock
        from contextlib import contextmanager

        @contextmanager
        def mock_db_query(dictionary=True):
            cursor = MagicMock()
            cursor.fetchone.return_value = {"user_id": 1, "name": "테스트직원암호화"}
            cursor.fetchall.return_value = [
                {
                    "evaluation_date": "2026-01-10",
                    "target_date": "2026-01-08",
                    "category": "신체",
                    "evaluation_type": "누락",
                    "comment": "테스트",
                }
            ]
            yield cursor

        with patch("backend.routers.feedback_reports.db_query", mock_db_query):
            with patch("backend.routers.feedback_reports.EncryptionService") as MockEnc:
                MockEnc.return_value.safe_decrypt.return_value = "홍길동"
                resp = client.post("/api/dashboard/employee/1/feedback-report", json=self.PAYLOAD)

        assert resp.status_code == 200
        data = resp.json()
        assert data["report_id"] == 1
        assert data["target_month"] == "2026-01"
        assert "ai_result" in data
        assert "summary_table" in data["ai_result"]

    def test_존재하지_않는_직원_404(self, client, mock_service):
        from unittest.mock import patch, MagicMock
        from contextlib import contextmanager

        @contextmanager
        def mock_db_query(dictionary=True):
            cursor = MagicMock()
            cursor.fetchone.return_value = None
            yield cursor

        with patch("backend.routers.feedback_reports.db_query", mock_db_query):
            resp = client.post("/api/dashboard/employee/999/feedback-report", json=self.PAYLOAD)

        assert resp.status_code == 404

    def test_AI_파싱_오류_500(self, client, mock_service):
        from unittest.mock import patch, MagicMock
        from contextlib import contextmanager

        mock_service.generate_and_save.side_effect = ValueError("AI 응답 JSON 파싱 오류")

        @contextmanager
        def mock_db_query(dictionary=True):
            cursor = MagicMock()
            cursor.fetchone.return_value = {"user_id": 1, "name": "enc_name"}
            cursor.fetchall.return_value = []
            yield cursor

        with patch("backend.routers.feedback_reports.db_query", mock_db_query):
            with patch("backend.routers.feedback_reports.EncryptionService") as MockEnc:
                MockEnc.return_value.safe_decrypt.return_value = "홍길동"
                resp = client.post("/api/dashboard/employee/1/feedback-report", json=self.PAYLOAD)

        assert resp.status_code == 500

    def test_비ADMIN_403(self, viewer_client, mock_service):
        resp = viewer_client.post(
            "/api/dashboard/employee/1/feedback-report", json=self.PAYLOAD
        )
        assert resp.status_code == 403


# ── GET: 목록 ────────────────────────────────────────────────────────────

class TestListFeedbackMonths:
    def test_목록_반환(self, client, mock_service):
        from unittest.mock import patch, MagicMock
        from contextlib import contextmanager

        @contextmanager
        def mock_db_query(dictionary=True):
            cursor = MagicMock()
            cursor.fetchone.return_value = {"user_id": 1}
            yield cursor

        with patch("backend.routers.feedback_reports.db_query", mock_db_query):
            resp = client.get("/api/dashboard/employee/1/feedback-reports")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["target_month"] == "2026-01"

    def test_존재하지_않는_직원_404(self, client, mock_service):
        from unittest.mock import patch, MagicMock
        from contextlib import contextmanager

        @contextmanager
        def mock_db_query(dictionary=True):
            cursor = MagicMock()
            cursor.fetchone.return_value = None
            yield cursor

        with patch("backend.routers.feedback_reports.db_query", mock_db_query):
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
```

- [ ] **Step 2b: 테스트 실행 — 실패 확인 (모듈 없음)**

```bash
pytest tests/backend/test_feedback_reports.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError` 또는 `ImportError` (아직 라우터 없음)

### Step 3: Schema + Router 구현

- [ ] **Step 3a: backend/schemas/feedback_reports.py 생성**

```python
"""직원 피드백 리포트 스키마"""

from pydantic import BaseModel
from typing import Optional, Any


class FeedbackReportCreate(BaseModel):
    target_month: str
    admin_note: Optional[str] = None


class FeedbackReportMonthItem(BaseModel):
    report_id: int
    target_month: str
    created_at: str


class FeedbackReportResponse(BaseModel):
    report_id: int
    user_id: int
    target_month: str
    admin_note: Optional[str]
    ai_result: Any
    created_at: str
    updated_at: str
```

- [ ] **Step 3b: backend/routers/feedback_reports.py 생성**

```python
"""직원 피드백 리포트 라우터"""

import calendar
from fastapi import APIRouter, Depends, HTTPException

from backend.dependencies import get_current_user, require_admin, get_feedback_service
from backend.encryption import EncryptionService
from backend.schemas.feedback_reports import (
    FeedbackReportCreate,
    FeedbackReportResponse,
    FeedbackReportMonthItem,
)
from modules.db_connection import db_query
from modules.services.feedback_service import FeedbackService

router = APIRouter(dependencies=[Depends(require_admin)])


@router.post("/dashboard/employee/{user_id}/feedback-report", response_model=FeedbackReportResponse)
def create_feedback_report(
    user_id: int,
    body: FeedbackReportCreate,
    service: FeedbackService = Depends(get_feedback_service),
):
    """AI 피드백 생성 & 저장 (ADMIN 전용)"""
    # 직원 조회
    with db_query() as cursor:
        cursor.execute("SELECT user_id, name FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="직원을 찾을 수 없습니다.")

    enc = EncryptionService()
    employee_name = enc.safe_decrypt(user["name"])

    # 해당 월 평가 이력 조회
    year, month = body.target_month.split("-")
    first_day = f"{year}-{month}-01"
    last_day_num = calendar.monthrange(int(year), int(month))[1]
    last_day = f"{year}-{month}-{last_day_num:02d}"

    with db_query() as cursor:
        cursor.execute(
            "SELECT evaluation_date, target_date, category, evaluation_type, comment "
            "FROM employee_evaluations "
            "WHERE target_user_id = %s AND evaluation_date BETWEEN %s AND %s "
            "ORDER BY evaluation_date",
            (user_id, first_day, last_day),
        )
        evaluations = cursor.fetchall()

    try:
        result = service.generate_and_save(
            user_id=user_id,
            employee_name=employee_name,
            target_month=body.target_month,
            admin_note=body.admin_note,
            evaluations=[dict(r) for r in evaluations],
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return result


@router.get("/dashboard/employee/{user_id}/feedback-reports", response_model=list[FeedbackReportMonthItem])
def list_feedback_months(
    user_id: int,
    service: FeedbackService = Depends(get_feedback_service),
):
    """저장된 월 목록 조회 (ADMIN 전용)"""
    with db_query() as cursor:
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="직원을 찾을 수 없습니다.")
    return service.list_months(user_id)


@router.get("/dashboard/employee/{user_id}/feedback-report/{month}", response_model=FeedbackReportResponse)
def get_feedback_report(
    user_id: int,
    month: str,
    service: FeedbackService = Depends(get_feedback_service),
):
    """특정 월 피드백 리포트 조회 (ADMIN 전용)"""
    result = service.get_by_month(user_id, month)
    if not result:
        raise HTTPException(status_code=404, detail="해당 월 피드백 리포트가 없습니다.")
    return result
```

- [ ] **Step 3c: backend/dependencies.py 에 의존성 추가**

`backend/dependencies.py` 의 import 섹션과 팩토리 함수에 추가.

파일 상단 import에 추가:
```python
from modules.repositories.feedback_report import FeedbackReportRepository
from modules.services.feedback_service import FeedbackService
```

파일 끝에 추가:
```python
def get_feedback_report_repo() -> FeedbackReportRepository:
    return FeedbackReportRepository()


def get_feedback_service(
    repo: FeedbackReportRepository = Depends(get_feedback_report_repo),
) -> FeedbackService:
    return FeedbackService(repo)
```

- [ ] **Step 3d: backend/main.py 라우터 등록**

`backend/main.py`의 import 블록에 추가:
```python
from backend.routers import (
    ...
    feedback_reports,   # 추가
)
```

`app.include_router(...)` 블록에 추가:
```python
app.include_router(feedback_reports.router, prefix="/api", tags=["피드백 리포트"])
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/backend/test_feedback_reports.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/schemas/feedback_reports.py backend/routers/feedback_reports.py \
        backend/dependencies.py backend/main.py \
        tests/backend/conftest.py tests/backend/test_feedback_reports.py
git commit -m "feat: 직원 피드백 리포트 백엔드 — schema/router/deps/테스트"
```

---

## Task 6: Frontend — Types + API

**Files:**
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/api/feedbackReports.ts`

- [ ] **Step 1: types/index.ts 에 타입 추가**

`frontend/src/types/index.ts` 끝에 추가:

```typescript
// ── 직원 피드백 리포트 ───────────────────────────────────────────────

export interface FeedbackReportMonthItem {
  report_id: number;
  target_month: string;
  created_at: string;
}

export interface FeedbackReportSummaryRow {
  구분: string;
  상세내용: string;
  비고: string;
}

export interface FeedbackReportImprovementExample {
  기존_작성방식: string;
  개선_작성방식: string;
}

export interface FeedbackReportAiResult {
  summary_table: FeedbackReportSummaryRow[];
  improvement_examples: FeedbackReportImprovementExample[];
}

export interface FeedbackReport {
  report_id: number;
  user_id: number;
  target_month: string;
  admin_note: string | null;
  ai_result: FeedbackReportAiResult;
  created_at: string;
  updated_at: string;
}
```

- [ ] **Step 2: api/feedbackReports.ts 생성**

```typescript
import api from "./client";
import type { FeedbackReport, FeedbackReportMonthItem } from "@/types";

export const feedbackReportsApi = {
  generate: (user_id: number, target_month: string, admin_note?: string | null) =>
    api
      .post<FeedbackReport>(`/dashboard/employee/${user_id}/feedback-report`, {
        target_month,
        admin_note: admin_note || null,
      })
      .then((r) => r.data),

  listMonths: (user_id: number) =>
    api
      .get<FeedbackReportMonthItem[]>(`/dashboard/employee/${user_id}/feedback-reports`)
      .then((r) => r.data),

  getByMonth: (user_id: number, month: string) =>
    api
      .get<FeedbackReport>(`/dashboard/employee/${user_id}/feedback-report/${month}`)
      .then((r) => r.data),
};
```

- [ ] **Step 3: 타입 체크**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: 에러 없음

- [ ] **Step 4: 커밋**

```bash
git add frontend/src/types/index.ts frontend/src/api/feedbackReports.ts
git commit -m "feat: FeedbackReport 타입 + feedbackReportsApi 추가"
```

---

## Task 7: Frontend — DashboardPage DetailsTab 서브탭

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx`

### 변경 전략
1. `DetailsTab` 컴포넌트 상단에 `subTab` state 추가 (`"history" | "feedback"`)
2. 서브탭 버튼 2개를 직원 선택 드롭다운 바로 아래 삽입
3. 기존 콘텐츠(`!selectedEmployee` 분기, KPI 카드, 차트, 폼, 테이블)를 `subTab === "history"` 블록으로 감싸기
4. `subTab === "feedback"` 블록에 `AiFeedbackPanel` 컴포넌트 인라인 구현

### AiFeedbackPanel 구성
- state: `targetMonth` (현재 월 기본값), `adminNote`, `generating`, `savedMonths`, `currentReport`, `loadingMonths`, `loadingReport`
- `useEffect`: `selectedEmployee` 변경 시 → `feedbackReportsApi.listMonths()` 호출
- "AI 피드백 생성" 버튼: `feedbackReportsApi.generate()` → toast → `savedMonths` + `currentReport` 갱신
- 저장된 월 뱃지 클릭: `feedbackReportsApi.getByMonth()` → `currentReport` 갱신
- 결과 영역: 피드백 요약 테이블 + 개선 예시 테이블

- [ ] **Step 1: DashboardPage.tsx import 추가**

`import { useState }` 를 다음으로 교체 (`useEffect` 추가):
```typescript
import { useState, useEffect } from "react";
```

파일 상단 기존 import 블록에 추가:
```typescript
import { feedbackReportsApi } from "@/api/feedbackReports";
import type { FeedbackReport, FeedbackReportMonthItem } from "@/types";
```

- [ ] **Step 2: DetailsTab 함수 상단에 subTab state 추가**

`DetailsTab` 함수 내 기존 state 선언들(예: `const [showForm, setShowForm]...`) 바로 위에 추가:
```typescript
const [subTab, setSubTab] = useState<"history" | "feedback">("history");
```

- [ ] **Step 3: 직원 선택 드롭다운 이후 서브탭 버튼 삽입**

`DetailsTab` 함수 내 직원 선택 `<div className="mb-4">...</div>` 바로 다음에 삽입:

```tsx
{/* 서브탭 */}
<div className="flex gap-1 mb-4 border-b border-gray-200">
  <button
    onClick={() => setSubTab("history")}
    className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
      subTab === "history"
        ? "border-blue-500 text-blue-600"
        : "border-transparent text-gray-500 hover:text-gray-700"
    }`}
  >
    평가 이력
  </button>
  <button
    onClick={() => setSubTab("feedback")}
    className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
      subTab === "feedback"
        ? "border-blue-500 text-blue-600"
        : "border-transparent text-gray-500 hover:text-gray-700"
    }`}
  >
    AI 피드백
  </button>
</div>
```

- [ ] **Step 4: 기존 콘텐츠를 history 조건으로 감싸기**

직원 선택 드롭다운과 서브탭 버튼 이후의 모든 JSX(`!selectedEmployee ? (` 분기부터 마지막 `: null}`)를 다음으로 감싸기:

```tsx
{subTab === "history" && (
  // 기존 코드 전체
)}
```

- [ ] **Step 5: AiFeedbackPanel 컴포넌트 추가**

서브탭 블록 이후(`{subTab === "history" && (...)}` 닫는 괄호 바로 다음)에 추가:

```tsx
{subTab === "feedback" && selectedEmployee && (
  <AiFeedbackPanel userId={selectedEmployee.user_id} />
)}
{subTab === "feedback" && !selectedEmployee && (
  <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
    직원을 선택하세요.
  </div>
)}
```

- [ ] **Step 6: AiFeedbackPanel 컴포넌트 함수 추가**

`DetailsTab` 함수 **바로 위** (같은 파일 안)에 추가:

```tsx
function AiFeedbackPanel({ userId }: { userId: number }) {
  const today = new Date();
  const defaultMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;

  const [targetMonth, setTargetMonth] = useState(defaultMonth);
  const [adminNote, setAdminNote] = useState("");
  const [generating, setGenerating] = useState(false);
  const [savedMonths, setSavedMonths] = useState<FeedbackReportMonthItem[]>([]);
  const [currentReport, setCurrentReport] = useState<FeedbackReport | null>(null);
  const [loadingMonths, setLoadingMonths] = useState(false);
  const [loadingReport, setLoadingReport] = useState(false);

  // 직원 변경 시 저장된 월 목록 로드
  useEffect(() => {
    setCurrentReport(null);
    setSavedMonths([]);
    setLoadingMonths(true);
    feedbackReportsApi
      .listMonths(userId)
      .then(setSavedMonths)
      .catch(() => {})
      .finally(() => setLoadingMonths(false));
  }, [userId]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const report = await feedbackReportsApi.generate(userId, targetMonth, adminNote || null);
      setCurrentReport(report);
      // 목록 갱신
      const months = await feedbackReportsApi.listMonths(userId);
      setSavedMonths(months);
      toast.success("AI 피드백이 생성되었습니다.");
    } catch {
      toast.error("피드백 생성 실패");
    } finally {
      setGenerating(false);
    }
  };

  const handleLoadMonth = async (month: string) => {
    setLoadingReport(true);
    try {
      const report = await feedbackReportsApi.getByMonth(userId, month);
      setCurrentReport(report);
    } catch {
      toast.error("피드백 로드 실패");
    } finally {
      setLoadingReport(false);
    }
  };

  // 최근 12개월 옵션 생성
  const monthOptions: string[] = [];
  for (let i = 0; i < 12; i++) {
    const d = new Date(today.getFullYear(), today.getMonth() - i, 1);
    monthOptions.push(
      `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`
    );
  }

  return (
    <div className="space-y-4">
      {/* 생성 컨트롤 */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="font-semibold text-gray-700 mb-3">AI 피드백 생성</h3>
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="text-xs text-gray-500 block mb-1">대상 월</label>
            <select
              value={targetMonth}
              onChange={(e) => setTargetMonth(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
            >
              {monthOptions.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
          <div className="flex-1 min-w-[200px]">
            <label className="text-xs text-gray-500 block mb-1">관리자 메모 (선택)</label>
            <input
              type="text"
              value={adminNote}
              onChange={(e) => setAdminNote(e.target.value)}
              placeholder="AI 참고용 메모 입력"
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="flex items-center gap-2 px-5 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {generating && <Loader2 size={14} className="animate-spin" />}
            AI 피드백 생성
          </button>
        </div>
      </div>

      {/* 저장된 월 뱃지 */}
      {loadingMonths ? (
        <div className="flex justify-center py-4">
          <Loader2 size={20} className="animate-spin text-gray-400" />
        </div>
      ) : savedMonths.length > 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs text-gray-500 mb-2">저장된 월</p>
          <div className="flex flex-wrap gap-2">
            {savedMonths.map((item) => (
              <button
                key={item.target_month}
                onClick={() => handleLoadMonth(item.target_month)}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                  currentReport?.target_month === item.target_month
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100"
                }`}
              >
                {item.target_month}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {/* 결과 영역 */}
      {loadingReport ? (
        <div className="flex justify-center py-8">
          <Loader2 size={24} className="animate-spin text-gray-400" />
        </div>
      ) : currentReport ? (
        <div className="space-y-4">
          {/* 피드백 요약 테이블 */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100">
              <h3 className="font-semibold text-gray-700">
                {currentReport.target_month} — 피드백 요약
              </h3>
              {currentReport.admin_note && (
                <p className="text-xs text-gray-400 mt-1">메모: {currentReport.admin_note}</p>
              )}
            </div>
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {["구분", "상세내용", "비고"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {currentReport.ai_result.summary_table.map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-xs font-medium text-gray-700 whitespace-nowrap">
                      {row.구분}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-600">{row.상세내용}</td>
                    <td className="px-4 py-3 text-xs text-gray-400 whitespace-nowrap">{row.비고}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 개선 예시 테이블 */}
          {currentReport.ai_result.improvement_examples.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-5 py-4 border-b border-gray-100">
                <h3 className="font-semibold text-gray-700">작성 방식 개선 예시</h3>
              </div>
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 w-1/2">
                      기존 작성방식
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 w-1/2">
                      개선 작성방식
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {currentReport.ai_result.improvement_examples.map((ex, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-xs text-gray-500">{ex.기존_작성방식}</td>
                      <td className="px-4 py-3 text-xs text-gray-700 font-medium">
                        {ex.개선_작성방식}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400 text-sm">
          대상 월을 선택하고 AI 피드백을 생성하거나, 저장된 월을 클릭하세요.
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 7: 타입 체크**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: 에러 없음

- [ ] **Step 8: 전체 테스트**

```bash
pytest tests/backend/test_feedback_reports.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 9: 커밋**

```bash
git add frontend/src/pages/DashboardPage.tsx
git commit -m "feat: DashboardPage DetailsTab — AI 피드백 서브탭 추가"
```

---

## Self-Review

### Spec Coverage

| 스펙 항목 | 구현 Task |
|-----------|-----------|
| `employee_feedback_reports` 테이블 | Task 1 |
| POST `/api/dashboard/employee/{user_id}/feedback-report` | Task 5 |
| GET 목록 | Task 5 |
| GET 단건 | Task 5 |
| ADMIN 전용 (403 테스트 포함) | Task 5 |
| XML 프롬프트 빌더 | Task 3 |
| AI 호출 → JSON 파싱 | Task 4 |
| upsert (같은 월 덮어쓰기) | Task 2 |
| AI 파싱 오류 → 500 | Task 5 |
| 없는 월 → 404 | Task 5 |
| 대상 월 드롭다운 (최근 12개월) | Task 7 |
| 관리자 메모 입력 | Task 7 |
| 저장된 월 뱃지 | Task 7 |
| 피드백 요약 테이블 | Task 7 |
| 개선 예시 테이블 | Task 7 |

### 주의사항

- `AiFeedbackPanel`은 `DetailsTab` **위**에 선언해야 함 (호이스팅 없음)
- `useState`/`useEffect` import 확인 — DashboardPage.tsx 에 이미 있어야 함
- `toast`는 기존 DashboardPage.tsx에 이미 import되어 있어야 함 (`sonner` 또는 `react-hot-toast` 확인 필요)
