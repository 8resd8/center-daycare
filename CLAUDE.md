## Language
모든 응답은 한국어로 작성하세요.

## Project
- 주간보호센터 내부 업무 관리 시스템
- PDF 업로드 → 주간상태변화 기록지 자동 생성
- 직원 평가 대시보드로 직원 관리

## 기술 스택
- 백엔드: FastAPI + Python 3.11
- 프론트엔드: React 18 + Vite + TypeScript + Tailwind CSS
- DB: MySQL (raw SQL, mysql.connector)
- AI: OpenAI
- 인증: JWT (httpOnly 쿠키, HS256)
- 암호화: Fernet AES-128 (ENCRYPTION_KEY 환경변수)

## 도메인 용어
| 한국어 | 영문(코드) | 설명 |
| 수급자 | Customer | 주간보호센터 이용자 |
| 직원 | Employee / User | 시설 직원 (시스템 사용자) |
| 기록지 | Daily Record | 일일 서비스 기록 |
| 주간 보고서 | Weekly Report | 주간 상태변화 AI 생성 보고서 |
| AI 평가 | AI Evaluation | 기록지 자동 평가 (우수/평균/개선) |
| 직원 평가 | Employee Evaluation | 직원 작성 오류/누락 수동 평가 |
| 지적 | Evaluation Point | 직원 평가의 오류/누락 1건 |

직원 평가 카테고리: `공통` / `신체` / `인지` / `간호` / `기능`
직원 평가 유형: `누락` / `내용부족` / `오타` / `문법` / `오류`
AI 평가 등급: `우수(excellent)=3점` / `평균(average)=2점` / `개선(improvement)=1점`

## 접근 권한 (RBAC)
| 역할 | DB 값 | 권한 |
| 관리자 | `ADMIN` | 모든 CRUD + PII 전체 조회 |
| 직원 | `EMPLOYEE` | Only 읽기 + PII 마스킹 적용 |

- ADMIN 전용 엔드포인트: `require_admin()` 의존성 사용
- ADMIN 외 역할: 응답에서 PII 자동 마스킹 (`apply_customer_mask()` / `apply_employee_mask()`)
- 감사 로깅: CREATE/UPDATE/DELETE 작업 → `audit_logs` 기록

## 개인정보(PII) 보호 규칙
암호화 대상: `customers`(name, birth_date, recognition_no, facility_name, facility_code) / `users`(name, birth_date)
- create/update 시 자동 Fernet 암호화, get/list 시 자동 복호화
- 비밀번호: bcrypt(rounds=12) 해시 (암호화 아님)
- 키워드 검색은 암호화로 SQL LIKE 불가 → Python 레이어 필터링

## Rules
- DB: `db_query()` / `db_transaction()` 컨텍스트 매니저만 사용
- 레이어: Repository → Service → UI 준수
- 테스트: DB/AI는 항상 mock 사용 (픽스처: `tests/conftest.py`)
- AI 호출: `modules/clients/ai_client.py` 통해서만 사용, 직접 SDK 호출 금지
- **잘못된 방식이나 실수할 때마다 CLAUDE.md에 내용 추가**
