# 아키텍처 가이드

## 레이어 구조

```
Router (backend/routers/)
  ↓  FastAPI 엔드포인트, 요청/응답 처리, 인증/인가 의존성
Service (modules/services/)
  ↓  비즈니스 로직, AI 호출 조율
Repository (modules/repositories/)
  ↓  DB 쿼리 (db_query / db_transaction 컨텍스트 매니저)
DB (MySQL)
```

**규칙**: 레이어를 건너뛰면 안 됨. Router → Repository 직접 호출 금지.

---

## 파일 맵

```
backend/
  main.py               FastAPI 앱, 라우터 등록, CORS, 미들웨어
  dependencies.py       get_current_user(), require_admin() 의존성
  encryption.py         EncryptionService (Fernet), apply_customer_mask(), apply_employee_mask()
  routers/              auth, customers, employees, daily_records,
                        weekly_reports, ai_evaluations, employee_evaluations,
                        dashboard, upload
  schemas/              Pydantic 스키마 (routers/ 와 1:1 대응)

modules/
  db_connection.py      db_query(), db_transaction() 컨텍스트 매니저
  clients/
    ai_client.py        BaseAIClient, OpenAIClient, set_ai_client()
    daily_prompt.py     일일 평가 AI 프롬프트
    weekly_prompt.py    주간 보고서 AI 프롬프트
  repositories/
    base.py             _execute_query, _execute_transaction 등 DB 추상화
    customer.py         CustomerRepository
    user.py             UserRepository
    daily_info.py       DailyInfoRepository
    weekly_status.py    WeeklyStatusRepository
    ai_evaluation.py    AiEvaluationRepository
    employee_evaluation.py  EmployeeEvaluationRepository
    audit.py            AuditRepository
  services/
    daily_report_service.py   EvaluationService (AI 평가)
    weekly_report_service.py  ReportService (주간 보고서 생성)
    analytics_service.py      분석 서비스
  pdf_parser.py         CareRecordParser (PDF → 구조화 데이터)
  weekly_data_analyzer.py  compute_weekly_status()

frontend/src/
  pages/                LoginPage, CareRecordsPage, DashboardPage,
                        CustomerManagePage, EmployeeManagePage
  api/                  client.ts (axios), 도메인별 api 파일, index.ts
  store/                authStore.ts (zustand), filterStore.ts
  types/index.ts        TypeScript 인터페이스 모음

tests/
  conftest.py           MockCursor, MockConnection, MockAIClient
  backend/conftest.py   FastAPI TestClient, set_test_encryption_key autouse
```

---

## 인증 / 인가

### JWT 흐름
- **Access Token**: 2시간, httpOnly 쿠키 (`path="/"`)
- **Refresh Token**: 7일, httpOnly 쿠키 (`path="/api/auth"`)
- 401 응답 시 프론트에서 자동 refresh 후 재시도

### RBAC

| 역할 | DB값 | 권한 |
|------|------|------|
| 관리자 | `ADMIN` | 모든 CRUD + PII 전체 조회 |
| 직원 | `EMPLOYEE` | 읽기 전용 + PII 마스킹 |

- ADMIN 전용: `Depends(require_admin())` 추가
- 비ADMIN 응답: `apply_customer_mask()` / `apply_employee_mask()` 적용
- 모든 라우터: `APIRouter(dependencies=[Depends(get_current_user)])` 기본 적용

### 감사 로그
CREATE / UPDATE / DELETE 작업마다 `audit_logs` 기록 필수.

---

## PII 암호화

**암호화 대상 컬럼**

| 테이블 | 컬럼 |
|--------|------|
| customers | name, birth_date, recognition_no, facility_name, facility_code |
| users | name, birth_date |

**규칙**
- create / update → `EncryptionService.encrypt()` 후 저장
- get / list → Repository에서 자동 복호화
- 비밀번호: bcrypt(rounds=12) — 암호화 아님, 해시
- 키워드 검색: SQL LIKE 불가 → Python 레이어에서 `safe_decrypt` 후 필터링
- `ENCRYPTION_KEY` 미설정 시 RuntimeError

---

## DB 접근 패턴

```python
# 조회
async with db_query() as cursor:
    await cursor.execute("SELECT ...", params)
    rows = await cursor.fetchall()

# 변경 (자동 commit/rollback)
async with db_transaction() as cursor:
    await cursor.execute("INSERT ...", params)
```

raw connection 직접 사용 금지.

---

## AI 클라이언트

```python
from modules.clients.ai_client import get_ai_client

client = get_ai_client()
response = await client.chat(messages=[...])
```

SDK 직접 호출 금지. 테스트 시 `set_ai_client(MockAIClient())`.

---

## 환경 변수

| 변수 | 기본값 | 필수 |
|------|--------|------|
| `ENCRYPTION_KEY` | 없음 | ✅ 필수 |
| `JWT_SECRET_KEY` | `"change-me-..."` | ✅ 운영 시 필수 |
| `JWT_ALGORITHM` | `HS256` | |
| `JWT_ACCESS_EXPIRE_HOURS` | `2` | |
| `JWT_REFRESH_EXPIRE_DAYS` | `7` | |
| `APP_ENV` | `development` | 쿠키 secure 플래그 결정 |

---

## 테스트 규칙

- DB: `MockCursor`, `MockConnection` 픽스처 사용 (`tests/conftest.py`)
- AI: `MockAIClient` 픽스처 사용
- 암호화: `set_test_encryption_key` autouse fixture 자동 적용
- Rate Limiter: autouse fixture로 slowapi storage reset 필수 (테스트 간 간섭)
- 암호화 컬럼 키워드 검색 테스트: SQL LIKE 파라미터 assert 금지

---

## 자주 하는 실수

| 실수 | 올바른 방법 |
|------|------------|
| 암호화 컬럼에 SQL LIKE | Python 레이어 `safe_decrypt` 후 필터링 |
| `birth_date`에 date 객체 전달 | 스키마 `coerce_birth_date` validator가 isoformat 변환 |
| `bcrypt>=5.0` 사용 | `bcrypt<5.0` pin 필수 (passlib 호환 오류) |
| Rate limit 테스트 순서 의존 | autouse fixture로 slowapi storage reset |
| Router에서 Repository 직접 호출 | Service 레이어 경유 필수 |
