## Language
모든 응답은 한국어로 작성하세요.

## 참조 문서
상세 내용은 docs를 참조하세요.
- [도메인 모델 / DB 스키마](docs/domain.md)
- [아키텍처 / 파일맵 / 보안 규칙](docs/architecture.md)
- [API 엔드포인트 레퍼런스](docs/api.md)

## 빌드 및 실행
```bash
uvicorn backend.main:app --reload        # 백엔드
cd frontend && npm run dev               # 프론트엔드
pytest                                   # 전체 테스트
pytest tests/backend/                    # 백엔드만
pytest -k test_name                      # 단일 테스트
cd frontend && npm run build             # 타입 체크 (tsc -b 포함)
```

## 아키텍처 규칙
- 레이어 순서: Router → Service → Repository (건너뜀 금지)
- DB: `db_query()` / `db_transaction()`만 사용 (raw connection 금지)
- AI: `modules/clients/ai_client.py`만 사용 (직접 SDK 호출 금지)
- 테스트: DB/AI mock 필수 — `tests/conftest.py` 픽스처 사용

## 접근 권한 (RBAC)
- ADMIN 전용 엔드포인트: `require_admin()` 의존성 사용
- 비ADMIN 응답: `apply_customer_mask()` / `apply_employee_mask()` 적용
- CREATE/UPDATE/DELETE → `audit_logs` 기록 필수

## PII 암호화
암호화 대상: `customers`(name, birth_date, recognition_no, facility_name, facility_code), `users`(name, birth_date)
- create/update → Fernet 암호화 / get/list → 복호화
- 키워드 검색: SQL LIKE 불가 → Python 레이어 필터링
- `ENCRYPTION_KEY` 미설정 시 RuntimeError

## 자주 하는 실수
- 암호화 컬럼 키워드 검색: SQL LIKE 쓰면 안 됨 — Python 레이어에서 `safe_decrypt` 후 필터링
- birth_date 타입 불일치: DB는 str, 스키마는 `Optional[str]` + `coerce_birth_date` validator (date 객체 → isoformat 자동 변환)
- bcrypt 버전 충돌: passlib는 bcrypt≥5.0 호환 안 됨 — `bcrypt<5.0` pin 필수
- Rate limit 테스트 간섭: slowapi storage를 autouse fixture로 reset 안 하면 테스트 순서에 따라 실패
- 키워드 테스트 SQL 검사 제거: `find_by_name`, `list_customers` 등에서 SQL LIKE 파라미터 assert 금지 (Python 필터링으로 변경됨)
- **잘못된 방식이나 실수할 때마다 이 섹션에 추가**
