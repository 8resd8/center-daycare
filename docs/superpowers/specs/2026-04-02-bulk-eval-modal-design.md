# 누락 항목 일괄 평가 등록 — 설계 문서

**날짜**: 2026-04-02
**범위**: 프론트엔드 전용 (백엔드 변경 없음)

---

## 배경 및 목표

일일 특이사항 평가에서 화장실·세면·특이사항·차량번호 등 필수 항목 누락을 수작업으로 하나씩 등록해야 하는 번거로움을 없앤다.
탭 행 옆 버튼 한 번으로 누락 항목을 모두 확인하고, 원하는 항목만 선택해 일괄 등록한다.

---

## 최종 결정 사항

| 항목 | 결정 |
|------|------|
| 버튼 위치 | 탭 행 (`주간상태변화 평가` / `일일 특이사항 평가`) 오른쪽 |
| 팝업 방식 | 모달 다이얼로그 |
| 등록 단위 | 누락 항목 1개 = 평가 1건 |
| 선택 방식 | 체크박스 개별 선택 + 전체 선택 토글 |
| 구현 위치 | `BulkEvalModal.tsx` 별도 컴포넌트 분리 |

---

## 파일 구조

```
frontend/src/
  components/
    BulkEvalModal.tsx     ← 신규
  pages/
    CareRecordsPage.tsx   ← 수정 (버튼 + 모달 마운트)
```

---

## 누락 항목 감지

기존 `checkRecord()` 함수를 그대로 활용한다. `false`인 항목만 추출한다 (`null`은 결석/일정없음이므로 제외).

### 필드 → (카테고리, 레이블, writer) 매핑

| checkRecord 키 | 필드명 | 카테고리 | writer 필드 |
|---|---|---|---|
| basic.총시간 | 총시간 | 공통 | writer_phy |
| basic.시작시간 | 시작시간 | 공통 | writer_phy |
| basic.종료시간 | 종료시간 | 공통 | writer_phy |
| basic.이동서비스 | 이동서비스 | 공통 | writer_phy |
| basic.차량번호 | 차량번호 | 공통 | writer_phy |
| physical.청결 | 청결(세면) | 신체 | writer_phy |
| physical.점심 | 점심 | 신체 | writer_phy |
| physical.저녁 | 저녁 | 신체 | writer_phy |
| physical.화장실 | 화장실 | 신체 | writer_phy |
| physical.이동도움 | 이동도움 | 신체 | writer_phy |
| physical.특이사항 | 특이사항 | 신체 | writer_phy |
| cognitive.인지관리 | 인지관리 | 인지 | writer_cog |
| cognitive.의사소통 | 의사소통 | 인지 | writer_cog |
| cognitive.특이사항 | 특이사항 | 인지 | writer_cog |
| nursing.혈압/체온 | 혈압/체온 | 간호 | writer_nur |
| nursing.건강관리 | 건강관리 | 간호 | writer_nur |
| nursing.특이사항 | 특이사항 | 간호 | writer_nur |
| recovery.향상프로그램 | 향상프로그램 | 기능 | writer_func |
| recovery.일상생활훈련 | 일상생활훈련 | 기능 | writer_func |
| recovery.인지활동프로그램 | 인지활동프로그램 | 기능 | writer_func |
| recovery.인지기능향상 | 인지기능향상 | 기능 | writer_func |
| recovery.특이사항 | 특이사항 | 기능 | writer_func |

---

## BulkEvalItem 타입

```typescript
type BulkEvalItem = {
  id: string;          // `${record_id}-${category}-${fieldLabel}` (고유 키)
  recordId: number;
  date: string;
  writerName: string;  // record의 해당 writer_xxx 값
  category: string;    // "공통" | "신체" | "인지" | "간호" | "기능"
  fieldLabel: string;  // "화장실", "차량번호" 등
  selected: boolean;
};
```

---

## BulkEvalModal 컴포넌트

### Props

```typescript
interface BulkEvalModalProps {
  open: boolean;
  onClose: () => void;
  records: DailyRecord[];
  users: UserDropdownItem[];  // /employee-evaluations/users 결과
}
```

### 내부 동작

1. **초기화**: `open`이 `true`로 바뀔 때 `records`에서 `checkRecord()` 실행 → `false` 항목만 추출 → `BulkEvalItem[]` 생성 (전체 `selected: true` 기본값)
2. **writer → user_id 매핑**: `users.find(u => u.name === writerName)` — 찾지 못하면 해당 항목을 목록에서 제외하고 경고 toast 출력
3. **전체 선택 토글**: 모두 선택 ↔ 모두 해제
4. **등록**: 선택된 항목을 순차적으로 `employeeEvaluationsApi.create()` 호출
   - `evaluation_date`: 오늘 날짜
   - `target_date`: 해당 record의 date
   - `evaluation_type`: `"누락"`
   - `score`: `1`
   - `comment`: `"{fieldLabel} 누락"`
   - 백엔드가 동일 `record_id + target_user_id + category + evaluation_type` 조합은 자동 upsert 처리함
5. **완료 후**: 성공/실패 건수 toast 출력, 모달 닫기

### UI 구성

```
┌─────────────────────────────────────────────┐
│ 누락 항목 자동 평가 등록         [N건 누락]  │
│ 등록할 항목을 선택하세요    [전체 선택/해제] │
├─────────────────────────────────────────────┤
│ ☑ 03-10 · 홍길동    신체 — 화장실           │
│ ☑ 03-10 · 홍길동    신체 — 특이사항         │
│ ☐ 03-11 · 홍길동    공통 — 차량번호         │
│ ☑ 03-12 · 홍길동    신체 — 청결(세면)       │
│   ...                                        │
├─────────────────────────────────────────────┤
│ [선택 항목 등록 (M건)]          [취소]       │
└─────────────────────────────────────────────┘
```

---

## CareRecordsPage 수정 내용

- `showBulkModal` state 추가
- 탭 행 오른쪽에 버튼 추가: 누락 항목이 0건이면 비활성화
- `<BulkEvalModal>` 마운트 (open/onClose/records/users 전달)
- `users` 데이터는 기존 `EmployeeEvalForm`과 동일한 쿼리 키 공유 (`"employee-eval-users"`)

---

## 예외 처리

| 상황 | 처리 |
|------|------|
| 누락 항목 0건 | 버튼 비활성화 (클릭 불가) |
| writer가 users 목록에 없음 | 해당 항목 제외 + "X명의 직원 정보를 찾지 못했습니다" toast |
| API 호출 일부 실패 | "N건 성공, M건 실패" toast |
| 모달 등록 중 닫기 | 등록 중에는 닫기 버튼 비활성화 |

---

## 범위 외 (이번 작업 미포함)

- 백엔드 변경
- 기존 `EmployeeEvalForm`의 `record_id` 버그 수정 (항상 첫 번째 레코드 사용)
- 등록 후 대시보드 자동 새로고침
