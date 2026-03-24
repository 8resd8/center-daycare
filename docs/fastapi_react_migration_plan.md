# FastAPI + React TypeScript 마이그레이션 계획

## 📋 개요

현재 Streamlit 기반의 요양기록 AI 매니저를 FastAPI + React TypeScript 아키텍처로 전환하는 계획입니다. 기존의 잘 구성된 3계층 아키텍처를 유지하며 UI 레이어만 현대적인 웹 기술로 교체합니다.

## 🎯 전환 목표

1. **기존 비즈니스 로직 100% 재사용**: repositories, services, pdf_parser는 그대로 유지
2. **향상된 사용자 경험**: 반응형 UI, 실시간 업데이트, 비동기 처리
3. **확장성**: API 기반 아키텍처로 모바일 앱 연동 용이
4. **유지보수성**: 타입스크립트 도입으로 런타임 오류 감소

## 🏗️ 현재 아키텍처 분석

### 기존 구조 (Streamlit)
```
Streamlit App
├── UI Layer (modules/ui/)
│   ├── sidebar.py (PDF 업로드)
│   ├── tabs_daily.py (일일 평가)
│   └── tabs_weekly.py (주간 리포트)
├── Service Layer (modules/services/)
│   ├── daily_report_service.py
│   ├── weekly_report_service.py
│   └── analytics_service.py
├── Repository Layer (modules/repositories/)
│   ├── daily_info.py
│   ├── customer.py
│   └── ai_evaluation.py
└── Core Components
    ├── pdf_parser.py (842줄)
    ├── ai_client.py (Gemini/GPT)
    └── database.py (MySQL)
```

### 목표 구조 (FastAPI + React)
```
React Frontend (Vite + TypeScript)
├── Components/
│   ├── FileUpload/
│   ├── DataTable/
│   ├── Charts/
│   └── Forms/
├── Pages/
│   ├── Dashboard/
│   ├── Records/
│   └── Management/
└── Hooks/ (TanStack Query)

FastAPI Backend
├── API Routes/
│   ├── records.py
│   ├── evaluations.py
│   ├── customers.py
│   └── reports.py
├── Service Layer (기존 재사용)
├── Repository Layer (기존 재사용)
└── Core Components (기존 재사용)
```

## 🔧 기술 스택 선정 이유

### Backend: FastAPI (Python)

#### ✅ 선택 이유
1. **기존 코드 재사용**: pdf_parser.py(842줄)를 그대로 사용 가능
2. **AI 연동 최적화**: Python SDK가 가장 성숙함 (Gemini/GPT)
3. **비동기 처리**: AI 응답 대기(수 초~수십 초)를 자연스럽게 처리
4. **자동 문서화**: OpenAPI/Swagger 자동 생성
5. **테스트 호환**: 기존 486개 테스트 그대로 유효

#### 🔄 전환 방식
```python
# 기존 Streamlit 흐름
sidebar.py → daily_report_service → DailyInfoRepository → MySQL

# FastAPI 전환 후
POST /api/records/upload → daily_report_service → DailyInfoRepository → MySQL
```

### Frontend: React + TypeScript (Vite)

#### ✅ Vite + React 선택 이유
1. **내부 도구 특화**: 인증된 사용자만 사용하므로 SSR/SEO 불필요
2. **개발 속도**: Vite의 빠른 핫 리로드
3. **오버엔지어링 방지**: Next.js의 서버 기능이 불필요
4. **컴포넌트 생태계**: shadcn/ui, Recharts 등 풍부한 라이브러리

#### 📦 권장 라이브러리
- **UI**: shadcn/ui (Tailwind CSS 기반)
- **상태 관리**: TanStack Query (서버 상태) + Zustand (클라이언트 상태)
- **폼**: React Hook Form + Zod
- **차트**: Recharts 또는 Nivo
- **라우팅**: React Router v6

## 📡 API 설계

### PDF 처리 및 기록 관리
```typescript
POST   /api/records/upload          // PDF 업로드 → 파싱 → DB 저장
GET    /api/records                 // 기록 목록 조회
GET    /api/records/{id}            // 특정 기록 조회
PUT    /api/records/{id}            // 기록 수정
DELETE /api/records/{id}            // 기록 삭제
```

### AI 평가 (비동기)
```typescript
POST   /api/evaluations             // 평가 요청 → task_id 반환
GET    /api/evaluations/{task_id}   // 결과 폴링
GET    /api/evaluations/stream      // SSE 실시간 결과 전송
```

### CRUD 관리
```typescript
// 고객 관리
GET    /api/customers               // 고객 목록
POST   /api/customers               // 고객 생성
PUT    /api/customers/{id}          // 고객 수정
DELETE /api/customers/{id}          // 고객 삭제

// 직원 관리
GET    /api/employees               // 직원 목록
POST   /api/employees               // 직원 생성
PUT    /api/employees/{id}          // 직원 수정
DELETE /api/employees/{id}          // 직원 삭제
```

### 리포트 및 분석
```typescript
POST   /api/reports/weekly          // 주간 리포트 생성
GET    /api/analytics/dashboard     // 대시보드 데이터
GET    /api/analytics/trends        // 트렌드 분석
```

## 🔄 기능 대응표

| 현재 (Streamlit) | 전환 후 (React) | 구현 방법 |
|------------------|----------------|----------|
| sidebar.py PDF 업로드 | `<FileUpload>` 컴포넌트 | fetch POST /api/records/upload |
| tabs_daily.py AI 평가 | `<EvaluationTable>` | TanStack Query + SSE |
| dashboard.py Altair 차트 | Recharts 컴포넌트 | GET /api/analytics/dashboard |
| customer_manage.py CRUD | `<CustomerCrudPage>` | REST API + React Hook Form |
| st.session_state | TanStack Query cache | 서버 상태 중심 관리 |

## ⚠️ 주의사항 및 해결책

### 1. PDF 파싱의 비동기 처리
**문제**: pdf_parser.py의 동기 코드가 FastAPI의 비동기 루프를 블로킹

**해결책**:
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

@router.post("/records/upload")
async def upload_pdf(file: UploadFile):
    loop = asyncio.get_event_loop()
    records = await loop.run_in_executor(
        None, parse_pdf_sync, file.file
    )
    return {"count": len(records)}
```

### 2. 메모리 관리
**문제**: 대용량 PDF 처리 시 메모리 부족

**해결책**: 기존의 gc.collect()와 청크 처리 로직 유지
```python
def parse_pdf_sync(file):
    try:
        # 기존 파싱 로직
        pass
    finally:
        gc.collect()  # 메모리 해제
```

### 3. AI 응답 시간 처리
**문제**: AI 평가에 수 초~수십 초 소요

**해결책**: 비동기 태스크 큐 + SSE
```python
@router.post("/evaluations")
async def start_evaluation(request: EvaluationRequest):
    task_id = str(uuid.uuid4())
    # 백그라운드 태스크 실행
    asyncio.create_task(process_evaluation(task_id, request))
    return {"task_id": task_id}

@router.get("/evaluations/{task_id}/stream")
async def stream_evaluation(task_id: str):
    # SSE로 실시간 결과 전송
    pass
```

## 📊 구현 우선순위

### Phase 1: 백엔드 API 기반 (2주)
1. FastAPI 프로젝트 설정
2. 기존 Service/Repository 연동
3. PDF 업로드 API 구현
4. 기본 CRUD API 구현
5. AI 평가 API (동기 버전)

### Phase 2: 프론트엔드 기본 (2주)
1. Vite + React + TypeScript 설정
2. 라우팅 및 레이아웃
3. 파일 업로드 컴포넌트
4. 데이터 테이블 컴포넌트
5. 기본 CRUD 폼

### Phase 3: 고급 기능 (2주)
1. AI 평가 비동기 처리 + SSE
2. 차트 및 대시보드
3. 실시간 업데이트
4. 반응형 디자인
5. 성능 최적화

### Phase 4: 테스트 및 배포 (1주)
1. API 테스트 (기존 486개 테스트 활용)
2. E2E 테스트
3. 배포 자동화
4. 모니터링 설정

## 🎯 성공 지표

1. **기능 동등성**: 기존 모든 기능 100% 이전
2. **성능 향상**: 페이지 로드 속도 50% 개선
3. **사용자 경험**: AI 응답 대기 시간 시각적 피드백 제공
4. **코드 재사용**: 핵심 비즈니스 로직 90% 이상 재사용
5. **테스트 커버리지**: 기존 테스트 100% 통과

## 🚀 장점 요약

1. **최소한의 리스크**: 기존 비즈니스 로직 그대로 유지
2. **빠른 개발**: 잘 정의된 API 레이어만 추가
3. **확장성**: 향후 모바일 앱 연동 용이
4. **현대화**: 반응형 UI, 실시간 업데이트, 타입 안정성
5. **유지보수**: 표준 웹 기술 스택으로 개발자 채용 용이

이 마이그레이션 계획은 기존 투자를 보호하면서 현대적인 웹 아키텍처의 이점을 모두 얻을 수 있는 최적의 방안입니다.
