# FastAPI + React TypeScript 학습 로드맵

## 📊 학습 시간 추정

### FastAPI (Python 기반)
| 항목 | 예상 시간 | 난이도 | 비고 |
|------|----------|--------|------|
| FastAPI 기초 (라우팅, 요청/응답) | 8시간 | ⭐⭐ | Python 기반이라 빠름 |
| Pydantic 모델링 | 4시간 | ⭐⭐ | 데이터 검증 |
| 비동기 처리 (async/await) | 12시간 | ⭐⭐⭐ | AI 연동 핵심 |
| 데이터베이스 연동 | 6시간 | ⭐⭐ | 기존 코드 재사용 |
| 인증/보안 | 8시간 | ⭐⭐⭐ | JWT, OAuth2 |
| 테스트 (pytest) | 6시간 | ⭐⭐ | 기존 테스트 활용 |
| 배포 (Docker) | 4시간 | ⭐⭐ | |
| **FastAPI 총계** | **48시간** | **약 1주** | |

### React + TypeScript
| 항목 | 예상 시간 | 난이도 | 비고 |
|------|----------|--------|------|
| React 기초 (컴포넌트, 상태) | 12시간 | ⭐⭐⭐ | 새로운 패러다임 |
| TypeScript 기초 | 8시간 | ⭐⭐ | 타입 시스템 |
| React Hooks | 8시간 | ⭐⭐⭐ | useState, useEffect |
| 상태 관리 (TanStack Query) | 10시간 | ⭐⭐⭐ | 서버 상태 |
| 폼 처리 (React Hook Form) | 6시간 | ⭐⭐ | |
| 라우팅 (React Router) | 4시간 | ⭐⭐ | |
| 스타일링 (Tailwind CSS) | 6시간 | ⭐⭐ | |
| 테스팅 (Jest, React Testing) | 8시간 | ⭐⭐⭐ | |
| **React 총계** | **62시간** | **약 1.5주** | |

### 총 학습 시간
- **순수 학습**: 110시간 (약 2.5주)
- **프로젝트 적용**: 40시간 (약 1주)
- **총 소요 시간**: **150시간 (약 3-4주)**

## 🎯 학습 전략

### Phase 1: FastAPI 집중 (1주)
**이유**: 기존 Python 코드와 친숙해서 빠른 성취감

#### Day 1-2: FastAPI 기초
```python
# 학습 목표
- FastAPI 프로젝트 구조 이해
- 기본 라우팅 (GET, POST, PUT, DELETE)
- 요청/응답 모델링
- 자동 API 문서화 활용

# 실습 과제
- 기존 daily_report_service를 API로 노출
- 간단한 CRUD 엔드포인트 구현
```

#### Day 3-4: 비동기 처리
```python
# 학습 목표
- async/await 개념 이해
- ThreadPoolExecutor로 블로킹 작업 처리
- AI 클라이언트 비동기 호출

# 실습 과제
- pdf_parser.py를 비동기로 감싸기
- AI 평가 API 비동기 구현
```

#### Day 5-7: 실전 적용
```python
# 학습 목표
- 기존 Service/Repository 연동
- 에러 처리 및 로깅
- 테스트 작성

# 실습 과제
- 전체 API 엔드포인트 구현
- 기존 테스트 통과 확인
```

### Phase 2: React + TypeScript (1.5주)
**이유**: 새로운 프론트엔드 패러다임 학습

#### Day 1-3: React + TypeScript 기초
```typescript
// 학습 목표
- 컴포넌트 기반 아키텍처
- Props와 State
- TypeScript 인터페이스
- JSX 문법

// 실습 과제
- 기본 컴포넌트 작성 (Header, Sidebar)
- 타입 정의 연습
```

#### Day 4-6: 상태 관리 및 데이터 페칭
```typescript
// 학습 목표
- TanStack Query 사용법
- React Hooks (useState, useEffect)
- API 연동

// 실습 과제
- 파일 업로드 컴포넌트
- 데이터 테이블 컴포넌트
- CRUD 폼 구현
```

#### Day 7-10: 고급 기능
```typescript
// 학습 목표
- React Hook Form + Zod
- Tailwind CSS
- 라우팅
- 차트 라이브러리

// 실습 과제
- 전체 페이지 구현
- 반응형 디자인
```

### Phase 3: 통합 및 실전 (0.5주)
**이유**: 배운 기술들을 실제 프로젝트에 적용

#### 통합 작업
- FastAPI와 React 연동
- CORS 설정
- 인증 구현
- 배포 준비

## 📚 추천 학습 자료

### FastAPI
1. **공식 문서**: https://fastapi.tiangolo.com/
2. **실전 예제**: 기존 코드를 API로 변환하는 연습
3. **테스트**: pytest로 API 테스트 작성

### React + TypeScript
1. **타입스크립트 핸드북**: https://www.typescriptlang.org/docs/
2. **React 공식 문서**: https://react.dev/
3. **TanStack Query 문서**: https://tanstack.com/query/latest
4. **shadcn/ui**: https://ui.shadcn.com/

## 🎖️ 학습 팁

### FastAPI 학습 팁
1. **기존 코드 활용**: pdf_parser, services를 그대로 사용하므로 새로운 API 레이어만 집중
2. **점진적 전환**: 먼저 동기 API로 만들고, 나중에 비동기로 전환
3. **테스트 활용**: 기존 486개 테스트가 안전망 역할

### React 학습 팁
1. **컴포넌트 중심**: Streamlit의 위젯 개념을 React 컴포넌트로 변환
2. **타입 먼저**: API 응답 타입부터 정의하면 개발이 쉬워짐
3. **상태 분리**: 서버 상태(TanStack Query)와 클라이언트 상태 분리

### 시간 관리 팁
1. **매일 3-4시간**: 꾸준함이 중요
2. **실습 중심**: 이론보다 코드 작성에 70% 시간 투자
3. **기존 코드 참조**: 이미 잘 동작하는 코드를 계속 참고하며 학습

## 🚀 성공 전략

### 1. 기존 자산 활용 극대화
- pdf_parser.py: 그대로 재사용 (842줄 절약)
- Service/Repository: API 레이어만 추가
- 테스트 코드: 486개 테스트가 안전망

### 2. 최소 기능 제품(MVP) 먼저
- 기본 CRUD + PDF 업로드
- AI 평가 (동기 버전)
- 간단한 데이터 표시

### 3. 점진적 개선
- MVP → 비동기 AI 처리 → 실시간 업데이트 → 고급 UI

## 📈 기대 효과

### 단기 (1개월)
- FastAPI + React 기반의 현대적 웹 앱
- 기존 기능 100% 이전
- API 기반 아키텍처 확보

### 중기 (3개월)
- 모바일 앱 연동 용이
- 실시간 협업 기능
- 성능 최적화

### 장기 (6개월)
- 마이크로서비스 아키텍처 전환 가능
- 타 서비스와 API 연동
- 개발 생산성 대폭 향상

이 학습 계획은 기존의 강력한 기반을 활용하므로, 일반적인 신규 프로젝트보다 훨씬 빠른 시간 내에 성공적인 마이그레이션이 가능할 것입니다.
