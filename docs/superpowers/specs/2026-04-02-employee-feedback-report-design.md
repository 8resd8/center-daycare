# 직원 피드백 리포트 — 설계 문서

**작성일**: 2026-04-02
**위치**: 대시보드 → 개별 리포트 탭 → AI 피드백 서브탭
**목적**: 직원의 월별 지적 이력을 기반으로 AI 피드백을 생성하여 더 나은 케어 기록 작성을 유도

---

## 1. 접근 권한

- **생성**: ADMIN 전용 (`require_admin()` 의존성)
- **조회**: ADMIN 전용
- EMPLOYEE 역할은 접근 불가

---

## 2. 데이터 모델

### 새 테이블: `employee_feedback_reports`

```sql
CREATE TABLE employee_feedback_reports (
  report_id    BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id      INT NOT NULL,
  target_month VARCHAR(7) NOT NULL,   -- 'YYYY-MM' 형식
  admin_note   TEXT,                  -- 관리자 메모 (AI 참고용, nullable)
  ai_result    JSON NOT NULL,         -- AI 생성 결과 (구조 아래 참조)
  created_at   DATETIME DEFAULT NOW(),
  updated_at   DATETIME DEFAULT NOW() ON UPDATE NOW(),
  UNIQUE KEY uq_user_month (user_id, target_month),
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
```

> DDL 적용은 직접 처리. 같은 월 재생성 시 **upsert (덮어쓰기)** 처리.

### `ai_result` JSON 구조

```json
{
  "summary_table": [
    { "구분": "오류",               "상세내용": "이동 도움 기재 오류 2회, 혈압 단위 오기 1회", "비고": "총 3건" },
    { "구분": "누락",               "상세내용": "인지 특이사항 미작성 5회, 간호 특이사항 미작성 2회", "비고": "총 7건" },
    { "구분": "횟수부족",           "상세내용": "이동 도움 내용 단순 기재 9회", "비고": "총 9건" },
    { "구분": "좋았던 부분",        "상세내용": "신체활동 기록 꾸준히 작성, 목욕 방법/시간 기재 성실", "비고": "" },
    { "구분": "개선해야 하는 부분", "상세내용": "인지 관리 특이사항에 어르신 반응 없이 행위만 단순 기재", "비고": "" },
    { "구분": "개선방법",           "상세내용": "프로그램명 + 어르신 반응 + 도움 내용 순으로 구체적으로 작성", "비고": "" }
  ],
  "improvement_examples": [
    {
      "기존_작성방식": "인지 프로그램 도움 드림",
      "개선_작성방식": "인지 프로그램(퍼즐 맞추기) 실시, 어르신께서 즐겁게 참여하시고 3개 완성하심"
    }
  ]
}
```

---

## 3. 백엔드 API

### 파일 구조

```
backend/
  routers/feedback_reports.py        # 엔드포인트 (3개)
  schemas/feedback_reports.py        # Pydantic 스키마
modules/
  services/feedback_service.py       # AI 호출 + 저장 로직
  repositories/feedback_report.py    # DB CRUD
  clients/feedback_prompt.py         # XML 구조 프롬프트 빌더
```

### 엔드포인트

| Method | Path | 설명 | 권한 |
|--------|------|------|------|
| `POST` | `/api/dashboard/employee/{user_id}/feedback-report` | AI 피드백 생성 & 저장 | ADMIN |
| `GET` | `/api/dashboard/employee/{user_id}/feedback-reports` | 저장된 월 목록 조회 → `[{"target_month": "2026-01", "created_at": "..."}]` | ADMIN |
| `GET` | `/api/dashboard/employee/{user_id}/feedback-report/{month}` | 특정 월 전체 결과 조회 → `FeedbackReportResponse` | ADMIN |

### POST 요청 body (Pydantic)

```python
class FeedbackReportCreate(BaseModel):
    target_month: str   # 'YYYY-MM' 형식, 예: '2026-01'
    admin_note: Optional[str] = None
```

### POST 처리 흐름

1. `require_admin()` 검증
2. `user_id`로 직원 조회 (없으면 404)
3. `target_month` 범위의 `employee_evaluations` 조회 (`evaluation_date` 기준: `YYYY-MM-01` ~ `YYYY-MM-마지막일`)
4. `feedback_prompt.py`로 XML 프롬프트 빌드
5. `get_ai_client().chat_completion()` 호출
6. AI 응답 JSON 파싱 및 유효성 검사
7. `employee_feedback_reports` upsert (`ON DUPLICATE KEY UPDATE`)
8. `audit_logs` 기록 (action: `CREATE` or `UPDATE`)
9. 저장된 결과 반환

---

## 4. AI 프롬프트

`modules/clients/feedback_prompt.py`에 구현.

### System 프롬프트

```xml
<role>
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
</output_format>
```

### User 프롬프트 (동적 빌드)

```xml
<target>
  <name>{직원명}</name>
  <month>{YYYY-MM}</month>
</target>

<!-- admin_note가 있을 때만 포함 -->
<admin_note>
  {관리자 메모 내용}
</admin_note>

<evaluation_history count="{건수}">
  <record>
    <evaluation_date>YYYY-MM-DD</evaluation_date>
    <target_date>YYYY-MM-DD</target_date>
    <category>인지</category>
    <evaluation_type>내용부족</evaluation_type>
    <comment>...</comment>
  </record>
  ...
</evaluation_history>

<instruction>
  위 지적 이력을 분석하여 직원이 더 나은 케어 기록을 작성할 수 있도록
  구체적이고 실용적인 피드백 리포트를 JSON으로 작성하세요.
</instruction>
```

---

## 5. 프론트엔드 UI

### 위치

`DashboardPage.tsx` → `DetailsTab` 컴포넌트 내부에 서브탭 추가

```
개별 리포트 탭
├── 직원 선택 드롭다운 (기존)
└── 서브탭
    ├── [평가 이력] — 기존 콘텐츠 그대로
    └── [AI 피드백] — 신규
```

### AI 피드백 서브탭 구성

**상단 컨트롤**
- 대상 월 드롭다운 (최근 12개월)
- 관리자 메모 텍스트 입력 (선택)
- "AI 피드백 생성" 버튼 (로딩 스피너 포함)

**저장된 결과 목록**
- 생성된 월을 뱃지로 표시, 클릭 시 해당 월 결과 로드

**결과 영역 — 테이블 1: 피드백 요약**

| 구분 | 상세내용 | 비고 |
|------|----------|------|
| 오류 | ... | 총 N건 |
| 누락 | ... | 총 N건 |
| 횟수부족 | ... | 총 N건 |
| 좋았던 부분 | ... | |
| 개선해야 하는 부분 | ... | |
| 개선방법 | ... | |

**결과 영역 — 테이블 2: 작성 방식 개선 예시**

| 기존 작성방식 | 개선 작성방식 |
|--------------|--------------|
| ... | ... |

### 신규 파일

```
frontend/src/
  api/feedbackReports.ts          # API 호출 함수
  types/index.ts                  # FeedbackReport 타입 추가
```

`DashboardPage.tsx`의 `DetailsTab` 컴포넌트 수정 (서브탭 추가).

---

## 6. 테스트

- `tests/backend/test_feedback_reports.py`
- DB / AI MockClient 픽스처 사용 (`tests/conftest.py`)
- 검증 항목:
  - POST: 생성 성공, upsert 동작, 비ADMIN 403
  - GET 목록: 저장된 월 반환
  - GET 단건: 결과 조회, 없는 월 404
  - AI 응답 파싱 오류 시 500 처리

---

## 7. 감사 로그

생성/재생성 시 `audit_logs` 기록:
- `action`: `CREATE` (신규) / `UPDATE` (재생성)
- `table_name`: `employee_feedback_reports`
- `record_id`: `report_id`
