## Language
모든 응답은 한국어로 작성하세요.

## 빌드 및 실행
```bash
uvicorn backend.main:app --reload        # 백엔드
cd frontend && npm run dev               # 프론트엔드
pytest                                   # 전체 테스트
pytest tests/backend/                    # 백엔드만
pytest -k test_name                      # 단일 테스트
cd frontend && npm run build             # 타입 체크 (tsc -b 포함)
```

## 파일 맵
```
backend/main.py              — FastAPI 진입점
backend/dependencies.py      — get_current_user, require_admin
backend/encryption.py        — EncryptionService, apply_*_mask
backend/routers/             — auth, customers, employees, daily_records,
                               weekly_reports, ai_evaluations,
                               employee_evaluations, dashboard, upload
backend/schemas/             — Pydantic 스키마
frontend/src/pages/          — CareRecordsPage, DashboardPage, LoginPage
frontend/src/api/            — axios 클라이언트 (withCredentials=true)
frontend/src/store/          — zustand (authStore)
modules/db_connection.py     — db_query / db_transaction 컨텍스트 매니저
modules/clients/ai_client.py — BaseAIClient, OpenAIClient; set_ai_client()
modules/repositories/        — CustomerRepository, UserRepository 등
modules/services/            — 비즈니스 로직 레이어
tests/conftest.py            — MockCursor, MockConnection, MockAIClient
tests/backend/conftest.py    — FastAPI TestClient, set_test_encryption_key
```

## 아키텍처 규칙
- 레이어 순서: Repository → Service → Router (건너뜀 금지)
- DB: `db_query()` / `db_transaction()`만 사용 (raw connection 금지)
- AI: `modules/clients/ai_client.py`만 사용 (직접 SDK 호출 금지)
- 테스트: DB/AI mock 필수 — `tests/conftest.py` 픽스처 사용

## 접근 권한 (RBAC)
| 역할 | DB 값 | 권한 |
|------|-------|------|
| 관리자 | `ADMIN` | 모든 CRUD + PII 전체 조회 |
| 직원 | `EMPLOYEE` | 읽기 전용 + PII 마스킹 |

- ADMIN 전용 엔드포인트: `require_admin()` 의존성 사용
- 비ADMIN: `apply_customer_mask()` / `apply_employee_mask()` 적용
- CREATE/UPDATE/DELETE → `audit_logs` 기록

## PII 암호화
암호화 대상: `customers`(name, birth_date, recognition_no, facility_name, facility_code), `users`(name, birth_date)
- create/update → Fernet 암호화 / get/list → 복호화
- 비밀번호: bcrypt(rounds=12) 해시 (암호화 아님)
- 키워드 검색: SQL LIKE 불가 → Python 레이어 필터링
- `ENCRYPTION_KEY` 미설정 시 RuntimeError
- 테스트: `set_test_encryption_key` autouse fixture 자동 설정

## 도메인 용어
| 한국어 | 영문(코드) | 설명 |
|--------|-----------|------|
| 수급자 | Customer | 주간보호센터 이용자 |
| 직원 | Employee / User | 시설 직원 (시스템 사용자) |
| 기록지 | Daily Record | 일일 서비스 기록 |
| 주간 보고서 | Weekly Report | 주간 상태변화 AI 생성 보고서 |
| AI 평가 | AI Evaluation | 기록지 자동 평가 |
| 직원 평가 | Employee Evaluation | 직원 작성 오류/누락 수동 평가 |
| 지적 | Evaluation Point | 직원 평가의 오류/누락 1건 |

카테고리: `공통` / `신체` / `인지` / `간호` / `기능`
유형: `누락` / `내용부족` / `오타` / `문법` / `오류`
AI 등급: `우수(excellent)=3점` / `평균(average)=2점` / `개선(improvement)=1점`

## 자주 하는 실수
- 암호화 컬럼 키워드 검색: SQL LIKE 쓰면 안 됨 — Python 레이어에서 `safe_decrypt` 후 필터링
- birth_date 타입 불일치: DB는 str, 스키마는 `Optional[str]` + `coerce_birth_date` validator (date 객체 → isoformat 자동 변환)
- bcrypt 버전 충돌: passlib는 bcrypt≥5.0 호환 안 됨 — `bcrypt<5.0` pin 필수
- Rate limit 테스트 간섭: slowapi storage를 autouse fixture로 reset 안 하면 테스트 순서에 따라 실패
- 키워드 테스트 SQL 검사 제거: `find_by_name`, `list_customers` 등에서 SQL LIKE 파라미터 assert 금지 (Python 필터링으로 변경됨)
- **잘못된 방식이나 실수할 때마다 이 섹션에 추가**
