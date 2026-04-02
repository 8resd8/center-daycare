# 누락 항목 일괄 평가 등록 V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 BulkEvalModal에 코멘트 수정·개별 등록·등록 취소·전체 수급자 모드·사이드바 초록색 표시 기능을 추가한다.

**Architecture:** Zustand 전역 스토어(`bulkEvalStore`)가 등록된 항목의 ID→evalId 매핑을 세션 내 유지하고, `useAllCustomerRecords` 훅이 전체 수급자 레코드를 React Query로 병렬 조회한다. BulkEvalModal은 단일/전체 모드를 모두 처리하며, Sidebar는 스토어를 읽어 수급자 이름 색상과 전체 등록 버튼을 제공한다.

**Tech Stack:** React 18, TypeScript 5.8, Zustand 5, @tanstack/react-query v5, Tailwind CSS, sonner (toast)

---

## 파일 맵

| 파일 | 변경 |
|------|------|
| `frontend/src/store/bulkEvalStore.ts` | 신규 — 등록 상태 전역 관리 |
| `frontend/src/hooks/useAllCustomerRecords.ts` | 신규 — 전체 수급자 레코드 병렬 조회 |
| `frontend/src/components/BulkEvalModal.tsx` | 수정 — 타입 확장 + 코멘트·개별 등록·취소 UI |
| `frontend/src/components/Sidebar.tsx` | 수정 — 초록색 표시 + 전체 누락 버튼 |
| `frontend/src/pages/CareRecordsPage.tsx` | 소폭 수정 — showCustomerName prop 추가 |

타입 체크 명령 (frontend 디렉토리 기준):
```bash
cd /c/git-project/arisa_internal_tool/frontend && node_modules/.bin/tsc --noEmit 2>&1
```

---

### Task 1: bulkEvalStore.ts 생성

**Files:**
- Create: `frontend/src/store/bulkEvalStore.ts`

- [ ] **Step 1: 파일 생성**

```typescript
// frontend/src/store/bulkEvalStore.ts
import { create } from "zustand";

type BulkEvalStore = {
  /** item.id → emp_eval_id (등록된 항목) */
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

- [ ] **Step 2: 타입 체크**

```bash
cd /c/git-project/arisa_internal_tool/frontend && node_modules/.bin/tsc --noEmit 2>&1
```
Expected: 오류 없음

- [ ] **Step 3: 커밋**

```bash
cd /c/git-project/arisa_internal_tool
git add frontend/src/store/bulkEvalStore.ts
git commit -m "feat: bulkEvalStore — 누락 항목 등록 상태 전역 관리"
```

---

### Task 2: useAllCustomerRecords.ts 생성

**Files:**
- Create: `frontend/src/hooks/useAllCustomerRecords.ts`

- [ ] **Step 1: 파일 생성**

```typescript
// frontend/src/hooks/useAllCustomerRecords.ts
import { useQueries } from "@tanstack/react-query";
import { useMemo } from "react";
import { dailyRecordsApi } from "@/api/dailyRecords";
import { useFilterStore } from "@/store/filterStore";
import type { DailyRecord, CustomerWithRecords } from "@/types";

/**
 * 전체 수급자의 일일 기록을 병렬 조회한다.
 * 캐시 키는 CareRecordsPage의 기존 쿼리와 동일하여 중복 API 요청이 발생하지 않는다.
 */
export function useAllCustomerRecords(customers: CustomerWithRecords[]): {
  allRecords: Map<number, DailyRecord[]>;
  isLoading: boolean;
} {
  const { startDate, endDate } = useFilterStore();

  const results = useQueries({
    queries: customers.map((c) => ({
      queryKey: ["daily-records", c.customer_id, startDate, endDate] as const,
      queryFn: () =>
        dailyRecordsApi.list({
          customer_id: c.customer_id,
          start_date: startDate ?? undefined,
          end_date: endDate ?? undefined,
        }),
      enabled: !!startDate && !!endDate && customers.length > 0,
    })),
  });

  const allRecords = useMemo(() => {
    const map = new Map<number, DailyRecord[]>();
    customers.forEach((c, i) => {
      const data = results[i]?.data;
      if (data) map.set(c.customer_id, data);
    });
    return map;
  }, [customers, results]);

  const isLoading = results.some((r) => r.isLoading);

  return { allRecords, isLoading };
}
```

- [ ] **Step 2: 타입 체크**

```bash
cd /c/git-project/arisa_internal_tool/frontend && node_modules/.bin/tsc --noEmit 2>&1
```
Expected: 오류 없음

- [ ] **Step 3: 커밋**

```bash
cd /c/git-project/arisa_internal_tool
git add frontend/src/hooks/useAllCustomerRecords.ts
git commit -m "feat: useAllCustomerRecords — 전체 수급자 레코드 병렬 조회 훅"
```

---

### Task 3: BulkEvalModal.tsx 대폭 수정

**Files:**
- Modify: `frontend/src/components/BulkEvalModal.tsx`

변경 요약:
- `BulkEvalItem` 타입에 `comment`, `status`, `evalId?`, `customerName?` 추가
- `buildBulkItems` export + `customerMap?` 파라미터 + 반환 타입을 `Omit<BulkEvalItem, "status"|"evalId">[]`로 변경
- Props에 `customerMap?`, `showCustomerName?` 추가
- `useBulkEvalStore`로 초기화 시 등록 상태 복원
- `processingIds` Set으로 개별 항목 로딩 추적
- `handleRegisterOne` / `handleCancelOne` 추가
- `handleRegister` (일괄) — pending+selected만 처리, 완료 후 모달 닫지 않음
- 항목 행 UI: pending/registered/failed 3가지 상태

- [ ] **Step 1: BulkEvalModal.tsx 전체 교체**

```typescript
// frontend/src/components/BulkEvalModal.tsx
import { useState, useEffect } from "react";
import { Loader2, X, CheckCircle2, XCircle } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { checkRecord } from "@/lib/careRecordCheck";
import { employeeEvaluationsApi } from "@/api/employeeEvaluations";
import { useBulkEvalStore } from "@/store/bulkEvalStore";
import type { DailyRecord, UserDropdownItem } from "@/types";
import type { CheckCategory } from "@/lib/careRecordCheck";

// ── 누락 항목 1건 단위 타입 ─────────────────────────────────────
export type BulkEvalItem = {
  id: string;            // `${recordId}-${category}-${fieldLabel}`
  recordId: number;
  date: string;
  customerName?: string; // 전체 수급자 모드에서 수급자명
  writerName: string;
  targetUserId: number;
  category: string;
  fieldLabel: string;
  comment: string;       // 수정 가능 코멘트, 기본값: `${fieldLabel} 누락`
  selected: boolean;
  status: "pending" | "registered" | "failed";
  evalId?: number;       // 등록 완료 시 저장 (취소 API 호출용)
};

// ── 필드 → (카테고리) 매핑 ──────────────────────────────────────
type FieldDef = { label: string; category: string };
const FIELD_DEFS: Record<CheckCategory, FieldDef[]> = {
  basic: [
    { label: "총시간", category: "공통" },
    { label: "시작시간", category: "공통" },
    { label: "종료시간", category: "공통" },
    { label: "이동서비스", category: "공통" },
    { label: "차량번호", category: "공통" },
  ],
  physical: [
    { label: "청결", category: "신체" },
    { label: "점심", category: "신체" },
    { label: "저녁", category: "신체" },
    { label: "화장실", category: "신체" },
    { label: "이동도움", category: "신체" },
    { label: "특이사항", category: "신체" },
  ],
  cognitive: [
    { label: "인지관리", category: "인지" },
    { label: "의사소통", category: "인지" },
    { label: "특이사항", category: "인지" },
  ],
  nursing: [
    { label: "혈압/체온", category: "간호" },
    { label: "건강관리", category: "간호" },
    { label: "특이사항", category: "간호" },
  ],
  recovery: [
    { label: "향상프로그램", category: "기능" },
    { label: "일상생활훈련", category: "기능" },
    { label: "인지활동프로그램", category: "기능" },
    { label: "인지기능향상", category: "기능" },
    { label: "특이사항", category: "기능" },
  ],
};

const WRITER_KEY: Record<CheckCategory, keyof DailyRecord> = {
  basic: "writer_phy",
  physical: "writer_phy",
  cognitive: "writer_cog",
  nursing: "writer_nur",
  recovery: "writer_func",
};

// ── 누락 항목 빌드 함수 (export) ──────────────────────────────────
export function buildBulkItems(
  records: DailyRecord[],
  users: UserDropdownItem[],
  customerMap?: Map<number, string>
): Omit<BulkEvalItem, "status" | "evalId">[] {
  const items: Omit<BulkEvalItem, "status" | "evalId">[] = [];
  const missingWriters = new Set<string>();

  for (const record of records) {
    const checked = checkRecord(record);
    const cats: CheckCategory[] = ["basic", "physical", "cognitive", "nursing", "recovery"];
    for (const cat of cats) {
      const catResult = checked[cat] as Record<string, boolean | null | string>;
      for (const def of FIELD_DEFS[cat]) {
        const val = catResult[def.label];
        if (val !== false) continue;
        const writerName = (record[WRITER_KEY[cat]] as string | null) ?? "";
        if (!writerName) continue;
        const user = users.find((u) => u.name === writerName);
        if (!user) {
          missingWriters.add(writerName);
          continue;
        }
        items.push({
          id: `${record.record_id}-${def.category}-${def.label}`,
          recordId: record.record_id,
          date: record.date,
          customerName: customerMap?.get(record.customer_id),
          writerName,
          targetUserId: user.user_id,
          category: def.category,
          fieldLabel: def.label,
          comment: `${def.label} 누락`,
          selected: true,
        });
      }
    }
  }

  if (missingWriters.size > 0) {
    toast.warning(
      `DB에서 찾을 수 없는 직원: ${[...missingWriters].join(", ")} — 해당 항목 제외됨`
    );
  }
  return items;
}

// ── 카테고리 색상 ───────────────────────────────────────────────
const CAT_COLOR: Record<string, string> = {
  공통: "bg-gray-100 text-gray-600",
  신체: "bg-orange-50 text-orange-600",
  인지: "bg-purple-50 text-purple-600",
  간호: "bg-blue-50 text-blue-600",
  기능: "bg-green-50 text-green-600",
};

// ── 메인 컴포넌트 ───────────────────────────────────────────────
interface BulkEvalModalProps {
  open: boolean;
  onClose: () => void;
  records: DailyRecord[];
  users: UserDropdownItem[];
  customerMap?: Map<number, string>; // customer_id → name (전체 모드)
  showCustomerName?: boolean;        // true면 수급자명 컬럼 표시
}

export default function BulkEvalModal({
  open,
  onClose,
  records,
  users,
  customerMap,
  showCustomerName = false,
}: BulkEvalModalProps) {
  const [items, setItems] = useState<BulkEvalItem[]>([]);
  const [registering, setRegistering] = useState(false);
  const [processingIds, setProcessingIds] = useState<Set<string>>(new Set());

  const { register, unregister } = useBulkEvalStore();

  // open될 때마다 누락 항목 재계산 + 스토어에서 등록 상태 복원
  useEffect(() => {
    if (!open) return;
    const { registeredItems } = useBulkEvalStore.getState();
    const baseItems = buildBulkItems(records, users, customerMap);
    setItems(
      baseItems.map((item) => {
        const evalId = registeredItems.get(item.id);
        return evalId !== undefined
          ? { ...item, status: "registered" as const, evalId }
          : { ...item, status: "pending" as const };
      })
    );
  }, [open, records, users, customerMap]);

  if (!open) return null;

  const pendingItems = items.filter((i) => i.status === "pending");
  const registeredCount = items.filter((i) => i.status === "registered").length;
  const selectedPending = pendingItems.filter((i) => i.selected);
  const allPendingSelected =
    pendingItems.length > 0 && pendingItems.every((i) => i.selected);

  const toggleAll = () => {
    setItems((prev) =>
      prev.map((i) =>
        i.status === "pending" ? { ...i, selected: !allPendingSelected } : i
      )
    );
  };

  const toggleItem = (id: string) => {
    setItems((prev) =>
      prev.map((i) =>
        i.id === id && i.status === "pending" ? { ...i, selected: !i.selected } : i
      )
    );
  };

  const updateComment = (id: string, comment: string) => {
    setItems((prev) => prev.map((i) => (i.id === id ? { ...i, comment } : i)));
  };

  const setProcessing = (id: string, on: boolean) => {
    setProcessingIds((prev) => {
      const next = new Set(prev);
      if (on) next.add(id);
      else next.delete(id);
      return next;
    });
  };

  const today = new Date().toISOString().slice(0, 10);

  const registerOne = async (item: BulkEvalItem): Promise<boolean> => {
    try {
      const evaluation = await employeeEvaluationsApi.create({
        record_id: item.recordId,
        target_user_id: item.targetUserId,
        category: item.category,
        evaluation_type: "누락",
        evaluation_date: today,
        target_date: item.date,
        evaluator_user_id: 1,
        score: 1,
        comment: item.comment,
      });
      const evalId = evaluation.emp_eval_id;
      setItems((prev) =>
        prev.map((i) =>
          i.id === item.id ? { ...i, status: "registered", evalId } : i
        )
      );
      register(item.id, evalId);
      return true;
    } catch {
      setItems((prev) =>
        prev.map((i) => (i.id === item.id ? { ...i, status: "failed" } : i))
      );
      return false;
    }
  };

  const handleRegisterOne = async (item: BulkEvalItem) => {
    setProcessing(item.id, true);
    await registerOne(item);
    setProcessing(item.id, false);
  };

  const handleCancelOne = async (item: BulkEvalItem) => {
    if (!item.evalId) return;
    setProcessing(item.id, true);
    try {
      await employeeEvaluationsApi.delete(item.evalId);
      setItems((prev) =>
        prev.map((i) =>
          i.id === item.id
            ? { ...i, status: "pending", evalId: undefined, selected: true }
            : i
        )
      );
      unregister(item.id);
    } catch {
      toast.error("등록 취소에 실패했습니다.");
    }
    setProcessing(item.id, false);
  };

  const handleRegister = async () => {
    if (selectedPending.length === 0) return;
    setRegistering(true);
    let success = 0,
      fail = 0;
    for (const item of selectedPending) {
      const ok = await registerOne(item);
      if (ok) success++;
      else fail++;
    }
    setRegistering(false);
    if (fail === 0) {
      toast.success(`${success}건 등록 완료`);
    } else {
      toast.warning(`${success}건 성공, ${fail}건 실패`);
    }
    // 모달 닫지 않음
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={() => {
        if (!registering) onClose();
      }}
    >
      <div
        className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 헤더 */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-bold text-gray-800">
              누락 항목 자동 평가 등록
            </span>
            <span className="bg-red-50 text-red-600 text-xs px-2 py-0.5 rounded-full font-medium">
              미등록 {pendingItems.length}건
            </span>
            {registeredCount > 0 && (
              <span className="bg-green-50 text-green-600 text-xs px-2 py-0.5 rounded-full font-medium">
                완료 {registeredCount}건
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            disabled={registering}
            aria-label="닫기"
            className="text-gray-400 hover:text-gray-600 disabled:opacity-40 ml-2 shrink-0"
          >
            <X size={18} />
          </button>
        </div>

        {/* 본문 */}
        <div className="px-5 py-3">
          {items.length === 0 ? (
            <p className="text-center text-sm text-gray-400 py-8">
              감지된 누락 항목이 없습니다.
            </p>
          ) : (
            <>
              {pendingItems.length > 0 && (
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs text-gray-500">
                    등록할 항목을 선택하세요
                  </span>
                  <button
                    onClick={toggleAll}
                    className="text-xs text-blue-600 hover:text-blue-700"
                  >
                    {allPendingSelected ? "전체 해제" : "전체 선택"}
                  </button>
                </div>
              )}

              <div className="flex flex-col gap-2 max-h-80 overflow-y-auto pr-0.5">
                {items.map((item) => {
                  const isProcessing = processingIds.has(item.id);

                  // ── 등록완료 행 ──────────────────────────────────────
                  if (item.status === "registered") {
                    return (
                      <div
                        key={item.id}
                        className="bg-green-50 border border-green-200 rounded-lg px-3 py-2"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <CheckCircle2
                            size={13}
                            className="text-green-500 shrink-0"
                          />
                          <span className="text-xs text-gray-500 w-10 shrink-0">
                            {item.date.slice(5)}
                          </span>
                          {showCustomerName && item.customerName && (
                            <span className="text-xs text-gray-700 shrink-0 max-w-[60px] truncate">
                              {item.customerName}
                            </span>
                          )}
                          <span className="text-xs text-gray-600 flex-1 truncate">
                            {item.writerName}
                          </span>
                          <span
                            className={cn(
                              "text-xs px-1.5 py-0.5 rounded-full shrink-0",
                              CAT_COLOR[item.category] ??
                                "bg-gray-100 text-gray-600"
                            )}
                          >
                            {item.category}—{item.fieldLabel}
                          </span>
                          <span className="text-xs text-green-600 font-medium shrink-0">
                            완료
                          </span>
                        </div>
                        <div className="flex items-center gap-2 pl-5">
                          <span className="text-xs text-gray-400 flex-1 truncate">
                            {item.comment}
                          </span>
                          <button
                            onClick={() => handleCancelOne(item)}
                            disabled={isProcessing}
                            className="text-xs px-2 py-0.5 border border-gray-200 text-gray-500 rounded hover:bg-gray-50 disabled:opacity-40 shrink-0 flex items-center gap-1"
                          >
                            {isProcessing && (
                              <Loader2 size={10} className="animate-spin" />
                            )}
                            등록 취소
                          </button>
                        </div>
                      </div>
                    );
                  }

                  // ── pending / failed 행 ──────────────────────────────
                  const isFailed = item.status === "failed";
                  return (
                    <div
                      key={item.id}
                      className={cn(
                        "rounded-lg px-3 py-2 transition-colors",
                        isFailed
                          ? "bg-red-50 border border-red-200"
                          : item.selected
                          ? "bg-orange-50 border border-orange-200 cursor-pointer"
                          : "bg-gray-50 border border-transparent opacity-60 cursor-pointer"
                      )}
                      onClick={() => !isFailed && toggleItem(item.id)}
                    >
                      <div className="flex items-center gap-2 mb-1.5">
                        {isFailed ? (
                          <XCircle
                            size={13}
                            className="text-red-400 shrink-0"
                          />
                        ) : (
                          <input
                            type="checkbox"
                            checked={item.selected}
                            onChange={(e) => {
                              e.stopPropagation();
                              toggleItem(item.id);
                            }}
                            className="w-3.5 h-3.5 accent-red-500 shrink-0"
                          />
                        )}
                        <span className="text-xs text-gray-500 w-10 shrink-0">
                          {item.date.slice(5)}
                        </span>
                        {showCustomerName && item.customerName && (
                          <span className="text-xs text-gray-700 shrink-0 max-w-[60px] truncate">
                            {item.customerName}
                          </span>
                        )}
                        <span className="text-xs text-gray-700 flex-1 truncate">
                          {item.writerName}
                        </span>
                        <span
                          className={cn(
                            "text-xs px-1.5 py-0.5 rounded-full shrink-0",
                            CAT_COLOR[item.category] ??
                              "bg-gray-100 text-gray-600"
                          )}
                        >
                          {item.category}—{item.fieldLabel}
                        </span>
                        {isFailed && (
                          <span className="text-xs text-red-500 shrink-0">
                            실패
                          </span>
                        )}
                      </div>
                      <div
                        className="flex items-center gap-2 pl-5"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <input
                          type="text"
                          value={item.comment}
                          onChange={(e) =>
                            updateComment(item.id, e.target.value)
                          }
                          className="flex-1 text-xs border border-gray-200 rounded px-2 py-1 focus:outline-none focus:border-blue-300 bg-white min-w-0"
                          placeholder="코멘트 입력"
                        />
                        <button
                          onClick={() => handleRegisterOne(item)}
                          disabled={isProcessing || registering}
                          className="text-xs px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600 disabled:opacity-40 shrink-0 flex items-center gap-1"
                        >
                          {isProcessing && (
                            <Loader2 size={10} className="animate-spin" />
                          )}
                          {isFailed ? "재시도" : "등록"}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>

        {/* 푸터 */}
        <div className="flex gap-2 px-5 py-4 border-t border-gray-100">
          <button
            onClick={handleRegister}
            disabled={registering || selectedPending.length === 0}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-red-500 text-white rounded-lg text-sm font-semibold hover:bg-red-600 disabled:opacity-40"
          >
            {registering && <Loader2 size={13} className="animate-spin" />}
            선택 항목 등록 ({selectedPending.length}건)
          </button>
          <button
            onClick={onClose}
            disabled={registering}
            className="px-4 py-2 border border-gray-200 text-gray-600 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-40"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 타입 체크**

```bash
cd /c/git-project/arisa_internal_tool/frontend && node_modules/.bin/tsc --noEmit 2>&1
```
Expected: 오류 없음

- [ ] **Step 3: 커밋**

```bash
cd /c/git-project/arisa_internal_tool
git add frontend/src/components/BulkEvalModal.tsx
git commit -m "feat: BulkEvalModal — 코멘트 수정·개별 등록·취소·완료 상태 표시"
```

---

### Task 4: Sidebar.tsx 수정

**Files:**
- Modify: `frontend/src/components/Sidebar.tsx`

다음 4가지를 순서대로 적용한다:
1. import 추가
2. 훅/상태 추가
3. 전체 누락 버튼 (조회 버튼 바로 아래)
4. 수급자 목록 색상 + BulkEvalModal 마운트

- [ ] **Step 1: import 6개 추가**

`Sidebar.tsx` 상단의 기존 import 블록 끝 (`import { useChunkedUpload } from "@/hooks/useChunkedUpload";` 다음 줄)에 추가:

기존 react import 수정:
```typescript
// 기존
import { useCallback, useRef, useState } from "react";
// 변경
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
```

그 아래 새 import 3줄 추가:
```typescript
import { useAllCustomerRecords } from "@/hooks/useAllCustomerRecords";
import { useBulkEvalStore } from "@/store/bulkEvalStore";
import BulkEvalModal, { buildBulkItems } from "@/components/BulkEvalModal";
import { employeeEvaluationsApi } from "@/api/employeeEvaluations";
```

- [ ] **Step 2: 훅과 상태 추가**

`Sidebar` 컴포넌트 내부, 기존 `const { upload, pause, resume, progress, phase, reset } = useChunkedUpload();` 바로 아래에 추가:

```typescript
  // users 쿼리 (BulkEvalModal과 동일한 캐시 키 공유)
  const { data: users = [] } = useQuery({
    queryKey: ["employee-eval-users"],
    queryFn: employeeEvaluationsApi.users,
    enabled: isRecordsPage,
  });

  // 전체 수급자 레코드 병렬 조회
  const { allRecords, isLoading: loadingAllRecords } = useAllCustomerRecords(
    isRecordsPage ? customersWithRecords : []
  );

  const { registeredItems, clear } = useBulkEvalStore();
  const [showAllBulkModal, setShowAllBulkModal] = useState(false);

  // 날짜 범위 변경 시 등록 상태 초기화
  useEffect(() => {
    clear();
  }, [startDate, endDate, clear]);

  // 수급자별 미등록 누락 항목 존재 여부
  const customerMissingSet = useMemo(() => {
    const set = new Set<number>();
    for (const [customerId, records] of allRecords) {
      const items = buildBulkItems(records, users);
      if (items.some((item) => !registeredItems.has(item.id))) {
        set.add(customerId);
      }
    }
    return set;
  }, [allRecords, users, registeredItems]);

  const missingCount = customerMissingSet.size;

  // 전체 수급자 모달용 customerMap, 전체 레코드 flat
  const customerMap = useMemo(
    () => new Map(customersWithRecords.map((c) => [c.customer_id, c.name])),
    [customersWithRecords]
  );

  const allRecordsFlat = useMemo(
    () => Array.from(allRecords.values()).flat(),
    [allRecords]
  );
```

- [ ] **Step 3: 전체 누락 버튼 추가 (조회 버튼 바로 아래)**

기존 조회 버튼:
```tsx
        <button onClick={handleSearch} className="mt-2 w-full text-xs bg-blue-600 text-white rounded py-1.5 hover:bg-blue-700">
          조회
        </button>
      </div>
```

다음으로 교체 (조회 버튼 바로 아래, 날짜 필터 `</div>` 닫기 전):
```tsx
        <button onClick={handleSearch} className="mt-2 w-full text-xs bg-blue-600 text-white rounded py-1.5 hover:bg-blue-700">
          조회
        </button>
        {isRecordsPage && (
          <button
            onClick={() => setShowAllBulkModal(true)}
            disabled={missingCount === 0 || loadingAllRecords}
            className="mt-1.5 w-full flex items-center justify-center gap-1 text-xs py-1.5 bg-red-50 text-red-600 border border-red-200 rounded-lg hover:bg-red-100 disabled:opacity-40 disabled:cursor-not-allowed font-medium"
          >
            {loadingAllRecords ? (
              <><Loader2 size={11} className="animate-spin" /> 누락 확인 중...</>
            ) : (
              `⚠ 전체 누락 일괄 등록${missingCount > 0 ? ` (${missingCount}명)` : ""}`
            )}
          </button>
        )}
      </div>
```

- [ ] **Step 4: 수급자 목록 색상 변경**

기존 수급자 버튼 className:
```tsx
                  className={cn(
                    "w-full text-left px-2 py-1.5 rounded-lg text-xs transition-colors",
                    selectedCustomerId === c.customer_id
                      ? "bg-blue-50 text-blue-700 font-medium"
                      : "text-gray-600 hover:bg-gray-100"
                  )}
```

다음으로 교체:
```tsx
                  className={cn(
                    "w-full text-left px-2 py-1.5 rounded-lg text-xs transition-colors",
                    selectedCustomerId === c.customer_id
                      ? "bg-blue-50 text-blue-700 font-medium"
                      : customerMissingSet.has(c.customer_id)
                      ? "text-green-600 hover:bg-gray-100 font-medium"
                      : "text-gray-600 hover:bg-gray-100"
                  )}
```

- [ ] **Step 5: BulkEvalModal 마운트 (return 최상단)**

`return (` 바로 다음, `<aside ...>` 태그 앞에 추가:
```tsx
    <>
      {isRecordsPage && (
        <BulkEvalModal
          open={showAllBulkModal}
          onClose={() => setShowAllBulkModal(false)}
          records={allRecordsFlat}
          users={users}
          customerMap={customerMap}
          showCustomerName={true}
        />
      )}
      <aside className="w-[240px] flex-shrink-0 bg-white border-r border-gray-200 flex flex-col overflow-y-auto">
```

그리고 기존 `</aside>` 닫기 태그 뒤에 `</>` 추가:
```tsx
      </aside>
    </>
```

- [ ] **Step 6: 타입 체크**

```bash
cd /c/git-project/arisa_internal_tool/frontend && node_modules/.bin/tsc --noEmit 2>&1
```
Expected: 오류 없음

- [ ] **Step 7: 커밋**

```bash
cd /c/git-project/arisa_internal_tool
git add frontend/src/components/Sidebar.tsx
git commit -m "feat: Sidebar — 전체 누락 일괄 등록 버튼 + 수급자 초록색 표시"
```

---

### Task 5: CareRecordsPage.tsx 소폭 수정 + 최종 검증

**Files:**
- Modify: `frontend/src/pages/CareRecordsPage.tsx`

- [ ] **Step 1: BulkEvalModal props 업데이트**

기존 BulkEvalModal JSX:
```tsx
      <BulkEvalModal
        open={showBulkModal}
        onClose={() => setShowBulkModal(false)}
        records={records}
        users={users}
      />
```

다음으로 교체:
```tsx
      <BulkEvalModal
        open={showBulkModal}
        onClose={() => setShowBulkModal(false)}
        records={records}
        users={users}
        showCustomerName={false}
      />
```

- [ ] **Step 2: 타입 체크**

```bash
cd /c/git-project/arisa_internal_tool/frontend && node_modules/.bin/tsc --noEmit 2>&1
```
Expected: 오류 없음

- [ ] **Step 3: 백엔드 테스트 통과 확인**

```bash
cd /c/git-project/arisa_internal_tool && python -m pytest tests/backend/ -q 2>&1
```
Expected: 220 passed (백엔드는 변경 없으므로 그대로)

- [ ] **Step 4: 커밋**

```bash
cd /c/git-project/arisa_internal_tool
git add frontend/src/pages/CareRecordsPage.tsx
git commit -m "feat: CareRecordsPage — BulkEvalModal showCustomerName prop 명시"
```
