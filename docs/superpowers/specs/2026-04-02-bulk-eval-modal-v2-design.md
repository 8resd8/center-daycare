# 누락 항목 일괄 평가 등록 V2 — 설계 문서

**날짜**: 2026-04-02
**범위**: 프론트엔드 전용 (백엔드 변경 없음)

---

## 배경 및 목표

V1(bulk-eval-modal)에서 구현된 누락 항목 일괄 등록 기능을 다음 네 가지 측면에서 개선한다:

1. 등록 후 "완료" 상태 표시 + 등록 취소
2. 전체 수급자에 대한 누락 확인 (사이드바 버튼)
3. 사이드바 수급자 목록 — 누락 있으면 초록색, 모두 등록 후 원래색 복귀
4. 항목별 코멘트 수정 후 개별/일괄 등록

---

## 최종 결정 사항

| 항목 | 결정 |
|------|------|
| 초록색 표시 시점 | 페이지 로드 시 자동 (전체 수급자 레코드 병렬 조회) |
| 전체 수급자 버튼 위치 | 사이드바 조회 버튼 바로 아래 |
| 등록 후 모달 동작 | 유지 + "✓ 완료 \| 등록 취소" 표시 |
| 코멘트 수정 UI | 항상 펼쳐진 인라인 입력 + 개별 등록 버튼 |
| 등록 취소 API | `DELETE /api/employee-evaluations/{id}` (이미 존재) |
| 프론트 API 메서드 | `employeeEvaluationsApi.delete(id)` (이미 존재) |

---

## 파일 구조

```
frontend/src/
  store/
    bulkEvalStore.ts           ← 신규
  hooks/
    useAllCustomerRecords.ts   ← 신규
  components/
    BulkEvalModal.tsx          ← 수정
    Sidebar.tsx                ← 수정
  pages/
    CareRecordsPage.tsx        ← 소폭 수정
```

---

## BulkEvalItem 타입 (변경)

```typescript
type BulkEvalItem = {
  id: string;              // `${recordId}-${category}-${fieldLabel}`
  recordId: number;
  date: string;
  customerName?: string;   // 전체 수급자 모드에서만 사용
  writerName: string;
  targetUserId: number;
  category: string;
  fieldLabel: string;
  comment: string;         // 수정 가능 코멘트. 기본값: `${fieldLabel} 누락`
  selected: boolean;
  status: "pending" | "registered" | "failed";
  evalId?: number;         // 등록 완료 시 저장 (취소 API 호출용)
};
```

---

## bulkEvalStore.ts (신규)

```typescript
import { create } from "zustand";

type BulkEvalStore = {
  // item.id → eval_id
  registeredItems: Map<string, number>;
  register: (itemId: string, evalId: number) => void;
  unregister: (itemId: string) => void;
  clear: () => void;
};

export const useBulkEvalStore = create<BulkEvalStore>((set) => ({
  registeredItems: new Map(),
  register: (itemId, evalId) =>
    set((s) => {
      const next = new Map(s.registeredItems);
      next.set(itemId, evalId);
      return { registeredItems: next };
    }),
  unregister: (itemId) =>
    set((s) => {
      const next = new Map(s.registeredItems);
      next.delete(itemId);
      return { registeredItems: next };
    }),
  clear: () => set({ registeredItems: new Map() }),
}));
```

세션 내 유지. 날짜/수급자 변경 시 `clear()` 호출.

---

## useAllCustomerRecords.ts (신규)

```typescript
// React Query useQueries로 전체 수급자 레코드 병렬 조회
// 반환: { allRecords: Map<number, DailyRecord[]>, isLoading: boolean }
// 캐시 키: ["daily-records", customerId, startDate, endDate]
//   → CareRecordsPage 기존 쿼리와 동일 → 중복 API 요청 없음
// 수급자 없음 / 날짜 미설정 → 빈 Map 반환
// 개별 조회 실패 → 해당 수급자 스킵 (콘솔 warn)
```

사이드바와 CareRecordsPage 양쪽에서 `import` 가능.

---

## Sidebar 변경

### 추가 데이터 조회

Sidebar에 `users` 쿼리 추가 (기존 CareRecordsPage와 동일 캐시 키 공유):

```typescript
const { data: users = [] } = useQuery({
  queryKey: ["employee-eval-users"],
  queryFn: employeeEvaluationsApi.users,
  enabled: isRecordsPage,
});
```

### 전체 누락 일괄 등록 버튼

조회 버튼 (날짜 범위 선택 UI) 바로 아래, 수급자 목록 위에 위치.

```
[🔴 전체 누락 일괄 등록 (N명 누락)]
```

- `N` = 미등록 누락 항목이 있는 수급자 수
- N = 0이면 비활성화
- 클릭 → `setShowAllBulkModal(true)` (Sidebar 내 state)
- `<BulkEvalModal>` 사이드바에도 마운트 (showCustomerName=true, 전체 수급자 records 전달)

### 수급자 목록 색상

```typescript
// 수급자별 미등록 누락 항목 존재 여부 계산
const customerMissingSet = useMemo(() => {
  const set = new Set<number>();
  for (const [customerId, records] of allRecords) {
    const items = buildBulkItems(records, users);
    const hasUnregistered = items.some(
      (item) => !registeredItems.has(item.id)
    );
    if (hasUnregistered) set.add(customerId);
  }
  return set;
}, [allRecords, users, registeredItems]);
```

```tsx
// 수급자 버튼 className
className={cn(
  "w-full text-left px-2 py-1.5 rounded-lg text-xs transition-colors",
  selectedCustomerId === c.customer_id
    ? "bg-blue-50 text-blue-700 font-medium"
    : customerMissingSet.has(c.customer_id)
    ? "text-green-600 hover:bg-gray-100 font-medium"  // 누락 있음
    : "text-gray-600 hover:bg-gray-100"               // 정상
)}
```

### 날짜 변경 시 스토어 초기화

날짜 범위가 바뀌면 `bulkEvalStore.clear()` 호출 (useEffect).

---

## BulkEvalModal 변경

### buildBulkItems export 변경

`buildBulkItems` 함수를 `export`로 변경하여 Sidebar의 `customerMissingSet` 계산에 재사용.
`customerName` 매핑을 위해 선택적 `customerMap` 파라미터 추가:

```typescript
export function buildBulkItems(
  records: DailyRecord[],
  users: UserDropdownItem[],
  customerMap?: Map<number, string>  // customer_id → name (전체 모드용)
): BulkEvalItem[]
```

`DailyRecord`에 `customer_id` 필드가 있으면 `customerMap.get(record.customer_id)` 로 `customerName` 설정.

### Props 변경

```typescript
interface BulkEvalModalProps {
  open: boolean;
  onClose: () => void;
  records: DailyRecord[];           // 단일 수급자 or 전체 수급자 합산 records
  users: UserDropdownItem[];
  customerMap?: Map<number, string>; // 전체 모드: customer_id → name
  showCustomerName?: boolean;        // true면 customerName 컬럼 표시
}
```

### 초기화 로직 변경

`open`이 `true`로 바뀔 때:
1. `buildBulkItems(records, users)` 실행
2. `bulkEvalStore.registeredItems`에 이미 있는 항목 → `status: "registered"`, `evalId` 설정
3. 없는 항목 → `status: "pending"`

### 항목 행 UI

**pending 상태:**
```
☑  03-10  홍길동  [신체—화장실]
           [화장실 누락_______________]  [등록]
```

**registered 상태 (초록 배경):**
```
✓  03-10  홍길동  [신체—특이사항]  등록완료
           특이사항 누락                          [등록 취소]
```
- 체크박스 없음, 코멘트 입력창 없음 (읽기 전용 텍스트)

**failed 상태 (빨간 테두리):**
```
✕  03-11  김철수  [인지—특이사항]  등록 실패
           [특이사항 누락_______________]  [재시도]
```

**전체 수급자 모드** (`showCustomerName=true`): `writerName` 앞에 `customerName` 컬럼 추가.

### 개별 등록

```typescript
const handleRegisterOne = async (item: BulkEvalItem) => {
  // API 호출 → 성공: status="registered", evalId=응답.id, store.register()
  //           → 실패: status="failed"
};
```

### 개별 취소

```typescript
const handleCancelOne = async (item: BulkEvalItem) => {
  // DELETE /api/employee-evaluations/{item.evalId}
  // 성공: status="pending", evalId=undefined, store.unregister()
};
```

### 일괄 등록

기존 `handleRegister` 로직 유지. `status === "pending" && selected`인 항목만 처리.
등록 완료 후 모달 닫지 않음.

### 헤더 카운터

```
누락 항목 자동 평가 등록  [미등록 N건 / 완료 M건]
```

---

## CareRecordsPage 변경

- 현재 수급자 records는 기존 쿼리 재사용 (변경 없음)
- `<BulkEvalModal>`에 `showCustomerName={false}` 명시 (단일 수급자 모드)
- `customerMap` prop 불필요 (단일 수급자)

---

## 예외 처리

| 상황 | 처리 |
|------|------|
| 전체 수급자 레코드 로딩 중 | 사이드바 버튼에 스피너 표시, 클릭 불가 |
| 개별 조회 실패 | 해당 수급자 스킵 (콘솔 warn) |
| 등록 취소 실패 | toast.error + status 유지 |
| 날짜 범위 변경 | bulkEvalStore.clear() + allRecords 재조회 |
| users 목록에 writer 없음 | 기존 동작 유지 (toast.warning + 항목 제외) |

---

## 범위 외 (이번 작업 미포함)

- 새로고침 후 등록 상태 복원 (localStorage 영속화)
- 등록 완료 항목의 대시보드 자동 갱신
- 백엔드 변경
