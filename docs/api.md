# API 엔드포인트 레퍼런스

모든 엔드포인트는 `/api` prefix. 기본 인증 필요 (`get_current_user`).
ADMIN 전용은 별도 표기.

---

## 인증 (`/api/auth`)

| Method | Path | 설명 | 제한 |
|--------|------|------|------|
| POST | `/auth/login` | 로그인 → 쿠키 발급 | 5회/분 |
| POST | `/auth/refresh` | Access Token 갱신 | |
| GET | `/auth/me` | 현재 사용자 정보 | |
| POST | `/auth/logout` | 쿠키 삭제 | |

---

## 수급자 (`/api/customers`)

| Method | Path | 설명 | 권한 |
|--------|------|------|------|
| GET | `/customers` | 목록 (`?keyword=`) | EMPLOYEE |
| GET | `/customers/{id}` | 상세 | EMPLOYEE |
| POST | `/customers` | 생성 | ADMIN |
| PUT | `/customers/{id}` | 수정 | ADMIN |
| DELETE | `/customers/{id}` | 삭제 | ADMIN |

---

## 직원 (`/api/employees`)

| Method | Path | 설명 | 권한 |
|--------|------|------|------|
| GET | `/employees` | 목록 (`?keyword=&work_status=`) | EMPLOYEE |
| GET | `/employees/{id}` | 상세 | EMPLOYEE |
| POST | `/employees` | 생성 | ADMIN |
| PUT | `/employees/{id}` | 수정 | ADMIN |
| DELETE | `/employees/{id}` | 퇴사 처리 (soft delete) | ADMIN |

---

## 일일 기록 (`/api/daily-records`)

| Method | Path | 설명 | 권한 |
|--------|------|------|------|
| GET | `/daily-records` | 목록 (`?customer_id=&start_date=&end_date=`) | EMPLOYEE |
| GET | `/daily-records/customers-with-records` | 기록 있는 수급자 목록 | EMPLOYEE |
| GET | `/daily-records/{id}` | 상세 | EMPLOYEE |
| DELETE | `/daily-records/{id}` | 삭제 | ADMIN |

---

## 주간 보고서 (`/api/weekly-reports`)

| Method | Path | 설명 | 권한 |
|--------|------|------|------|
| GET | `/weekly-reports` | 목록 (`?customer_id=&start_date=&end_date=`) | EMPLOYEE |
| GET | `/weekly-reports/analysis` | 전주/이번주 변화량 분석 | EMPLOYEE |
| POST | `/weekly-reports/generate` | AI 보고서 생성 | ADMIN |
| PUT | `/weekly-reports/{customer_id}` | 보고서 저장 | ADMIN |

---

## AI 평가 (`/api/ai-evaluations`)

| Method | Path | 설명 | 권한 |
|--------|------|------|------|
| GET | `/ai-evaluations` | 기록별 평가 조회 (`?record_id=`) | EMPLOYEE |
| POST | `/ai-evaluations/evaluate` | 특정 항목 평가 | ADMIN |
| POST | `/ai-evaluations/evaluate-record/{record_id}` | 전체 기록 평가 | ADMIN |

---

## 직원 평가 (`/api/employee-evaluations`)

| Method | Path | 설명 | 권한 |
|--------|------|------|------|
| GET | `/employee-evaluations/users` | 직원 드롭다운 목록 | EMPLOYEE |
| GET | `/employee-evaluations` | 기록별 평가 조회 (`?record_id=`) | EMPLOYEE |
| POST | `/employee-evaluations` | 평가 생성 | ADMIN |
| PUT | `/employee-evaluations/{id}` | 평가 수정 | ADMIN |
| DELETE | `/employee-evaluations/{id}` | 평가 삭제 | ADMIN |

---

## 대시보드 (`/api/dashboard`)

모두 `?start_date=&end_date=` 필터 지원.

| Method | Path | 설명 |
|--------|------|------|
| GET | `/dashboard/summary` | KPI 요약 (수급자/직원/기록/평균등급) |
| GET | `/dashboard/evaluation-trend` | AI 평가 등급 추이 |
| GET | `/dashboard/employee-rankings` | 직원별 기록/평가 랭킹 |
| GET | `/dashboard/ai-grade-dist` | AI 등급 분포 |
| GET | `/dashboard/employee/{id}/details` | 직원별 기록/평가 상세 |
| GET | `/dashboard/emp-eval-trend` | 직원 평가 유형별 일별 추이 |
| GET | `/dashboard/emp-eval-category` | 직원 평가 카테고리별 건수 |
| GET | `/dashboard/emp-eval-rankings` | 직원별 지적 건수 랭킹 |
| GET | `/dashboard/employee/{id}/emp-eval-history` | 직원별 지적 이력 |
| GET | `/dashboard/period-comparison` | 기간별 유형 비교 |
| GET | `/dashboard/kpi-summary` | KPI 카드 + delta |
| GET | `/dashboard/employee/{id}/monthly-trend` | 직원별 월별 지적 건수 |

---

## 파일 업로드 (`/api/upload`)

모두 ADMIN 전용.

| Method | Path | 설명 |
|--------|------|------|
| POST | `/upload` | PDF 업로드 (단일, 즉시 파싱) |
| GET | `/upload/{file_id}/preview` | 파싱 미리보기 |
| POST | `/upload/{file_id}/save` | DB 저장 |
| POST | `/upload/chunk/init` | 청크 업로드 세션 초기화 |
| PUT | `/upload/chunk/{upload_id}` | 청크 전송 |
| GET | `/upload/chunk/{upload_id}/status` | 업로드 진행 상황 |
| POST | `/upload/chunk/{upload_id}/complete` | 병합 및 파싱 |
