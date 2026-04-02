# 누락 항목 일괄 평가 등록 (BulkEvalModal) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 일일 특이사항 평가 탭 옆 버튼 클릭으로 필수 항목 누락을 감지하고, 체크박스로 선택한 항목을 일괄 직원 평가로 등록한다.

**Architecture:** 기존 `checkRecord()` 로직을 `src/lib/careRecordCheck.ts`로 분리하여 재사용하고, `BulkEvalModal.tsx` 신규 컴포넌트에서 누락 감지·체크박스 UI·API 등록을 담당한다. `CareRecordsPage.tsx`는 버튼과 모달 마운트만 추가한다. 백엔드 변경 없음.

**Tech Stack:** React 18, TypeScript 5.8, @radix-ui/react-dialog, @tanstack/react-query, sonner(toast), lucide-react

---

## 파일 구조

| 상태 | 경로 | 역할 |
|------|------|------|
| **신규** | `frontend/src/lib/careRecordCheck.ts` | `checkRecord()` + 타입 export |
| **신규** | `frontend/src/components/BulkEvalModal.tsx` | 누락 감지·체크박스 UI·등록 로직 |
| **수정** | `frontend/src/pages/CareRecordsPage.tsx` | `checkRecord` import 교체, `users` 쿼리 상단 이동, 버튼·모달 추가 |

---

## Task 1: checkRecord 유틸 분리

**Files:**
- Create: `frontend/src/lib/careRecordCheck.ts`
- Modify: `frontend/src/pages/CareRecordsPage.tsx` (import 교체, 로컬 정의 제거)

- [ ] **Step 1: `careRecordCheck.ts` 생성**

```typescript
// frontend/src/lib/careRecordCheck.ts
import type { DailyRecord } from "@/types";

export function checkRecord(r: DailyRecord) {
  const absent = ["미이용", "결석", "일정없음"].includes((r.total_service_time ?? "").trim());
  const endHour = r.end_time ? parseInt(r.end_time.split(":")[0] ?? "0") : 0;
  const endMin = r.end_time ? parseInt(r.end_time.split(":")[1] ?? "0") : 0;
  const isAfternoon = endHour > 17 || (endHour === 17 && endMin >= 10);
  const mk = (v: string | null | undefined) => absent ? null : !!v?.trim();
  return {
    date: r.date,
    basic: { 총시간: mk(r.total_service_time), 시작시간: mk(r.start_time), 종료시간: mk(r.end_time), 이동서비스: mk(r.transport_service), 차량번호: mk(r.transport_vehicles), writer: r.writer_phy ?? "" },
    physical: { 청결: mk(r.hygiene_care), 점심: mk(r.meal_lunch), 저녁: absent ? null : (isAfternoon ? !!r.meal_dinner?.trim() : null), 화장실: mk(r.toilet_care), 이동도움: mk(r.mobility_care), 특이사항: mk(r.physical_note), writer: r.writer_phy ?? "" },
    cognitive: { 인지관리: mk(r.cog_support), 의사소통: mk(r.comm_support), 특이사항: mk(r.cognitive_note), writer: r.writer_cog ?? "" },
    nursing: { "혈압/체온": mk(r.bp_temp), 건강관리: mk(r.health_manage), 특이사항: mk(r.nursing_note), writer: r.writer_nur ?? "" },
    recovery: { 향상프로그램: mk(r.prog_basic), 일상생활훈련: mk(r.prog_activity), 인지활동프로그램: mk(r.prog_cognitive), 인지기능향상: mk(r.prog_therapy), 특이사항: mk(r.functional_note), writer: r.writer_func ?? "" },
  };
}

export type CheckResult = ReturnType<typeof checkRecord>;
export type CheckCategory = "basic" | "physical" | "cognitive" | "nursing" | "recovery";

export function calcRate(results: CheckResult[], cat: CheckCategory) {
  let total = 0, done = 0;
  for (const r of results) {
    const checks = r[cat] as Record<string, boolean | null | string>;
    for (const [k, v] of Object.entries(checks)) {
      if (k === "writer" || v === null) continue;
      total++;
      if (v) done++;
    }
  }
  return total === 0 ? 100 : Math.round((done / total) * 1000) / 10;
}
```

- [ ] **Step 2: `CareRecordsPage.tsx` 상단 import 교체**

파일 상단에서 아래 로컬 정의 3개를 제거하고 import로 교체한다.

제거할 코드 (`CareRecordsPage.tsx` line 43~72):
```typescript
// ── 필수항목 체크 ──────────────────────────────────────────────
function checkRecord(r: DailyRecord) { ... }
type CheckResult = ReturnType<typeof checkRecord>;
type CheckCategory = "basic" | "physical" | "cognitive" | "nursing" | "recovery";

function calcRate(results: CheckResult[], cat: CheckCategory) { ... }
```

추가할 import (파일 최상단 import 블록 끝에):
```typescript
import { checkRecord, calcRate } from "@/lib/careRecordCheck";
import type { CheckResult, CheckCategory } from "@/lib/careRecordCheck";
```

- [ ] **Step 3: 타입 체크**

```bash
cd /c/git-project/arisa_internal_tool/.worktrees/feature/bulk-eval-modal/frontend && node_modules/.bin/tsc --noEmit
```

오류 없음 확인.

- [ ] **Step 4: 커밋**

```bash
cd /c/git-project/arisa_internal_tool/.worktrees/feature/bulk-eval-modal
git add frontend/src/lib/careRecordCheck.ts frontend/src/pages/CareRecordsPage.tsx
git commit -m "refactor: checkRecord/calcRate 유틸을 careRecordCheck.ts로 분리"
```

---

## Task 2: BulkEvalModal 컴포넌트 구현

**Files:**
- Create: `frontend/src/components/BulkEvalModal.tsx`

- [ ] **Step 1: `BulkEvalModal.tsx` 생성**

```typescript
// frontend/src/components/BulkEvalModal.tsx
import { useState, useEffect, useRef } from "react";
import { Loader2, X } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { checkRecord } from "@/lib/careRecordCheck";
import { employeeEvaluationsApi } from "@/api/employeeEvaluations";
import type { DailyRecord, UserDropdownItem } from "@/types";
import type { CheckCategory } from "@/lib/careRecordCheck";

// ── 누락 항목 1건 단위 타입 ─────────────────────────────────────
type BulkEvalItem = {
  id: string;           // `${recordId}-${category}-${fieldLabel}`
  recordId: number;
  date: string;
  writerName: string;
  targetUserId: number;
  category: string;
  fieldLabel: string;
  selected: boolean;
};

// ── 필드 → (카테고리, writer 키) 매핑 ──────────────────────────
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

// ── 누락 항목 빌드 함수 ─────────────────────────────────────────
function buildBulkItems(records: DailyRecord[], users: UserDropdownItem[]): BulkEvalItem[] {
  const items: BulkEvalItem[] = [];
  const missingWriters = new Set<string>();

  for (const record of records) {
    const checked = checkRecord(record);
    const cats: CheckCategory[] = ["basic", "physical", "cognitive", "nursing", "recovery"];
    for (const cat of cats) {
      const catResult = checked[cat] as Record<string, boolean | null | string>;
      for (const def of FIELD_DEFS[cat]) {
        const val = catResult[def.label];
        if (val !== false) continue; // true(정상) or null(결석) 제외
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
          writerName,
          targetUserId: user.user_id,
          category: def.category,
          fieldLabel: def.label,
          selected: true,
        });
      }
    }
  }

  if (missingWriters.size > 0) {
    toast.warning(`DB에서 찾을 수 없는 직원: ${[...missingWriters].join(", ")} — 해당 항목 제외됨`);
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
}

export default function BulkEvalModal({ open, onClose, records, users }: BulkEvalModalProps) {
  const [items, setItems] = useState<BulkEvalItem[]>([]);
  const [registering, setRegistering] = useState(false);
  const initialized = useRef(false);

  // open될 때마다 누락 항목 재계산
  useEffect(() => {
    if (open) {
      initialized.current = false;
      setItems(buildBulkItems(records, users));
      initialized.current = true;
    }
  }, [open, records, users]);

  if (!open) return null;

  const selectedItems = items.filter((i) => i.selected);
  const allSelected = items.length > 0 && items.every((i) => i.selected);

  const toggleAll = () => {
    setItems((prev) => prev.map((i) => ({ ...i, selected: !allSelected })));
  };

  const toggleItem = (id: string) => {
    setItems((prev) => prev.map((i) => i.id === id ? { ...i, selected: !i.selected } : i));
  };

  const handleRegister = async () => {
    if (selectedItems.length === 0) return;
    setRegistering(true);
    const today = new Date().toISOString().slice(0, 10);
    let success = 0, fail = 0;

    for (const item of selectedItems) {
      try {
        await employeeEvaluationsApi.create({
          record_id: item.recordId,
          target_user_id: item.targetUserId,
          category: item.category,
          evaluation_type: "누락",
          evaluation_date: today,
          target_date: item.date,
          evaluator_user_id: 1,
          score: 1,
          comment: `${item.fieldLabel} 누락`,
        });
        success++;
      } catch {
        fail++;
      }
    }

    setRegistering(false);
    if (fail === 0) {
      toast.success(`${success}건 등록 완료`);
    } else {
      toast.warning(`${success}건 성공, ${fail}건 실패`);
    }
    onClose();
  };

  return (
    // 모달 오버레이
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 헤더 */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-gray-800">누락 항목 자동 평가 등록</span>
            {items.length > 0 && (
              <span className="bg-red-50 text-red-600 text-xs px-2 py-0.5 rounded-full font-medium">
                {items.length}건 감지
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            disabled={registering}
            className="text-gray-400 hover:text-gray-600 disabled:opacity-40"
          >
            <X size={18} />
          </button>
        </div>

        {/* 본문 */}
        <div className="px-5 py-3">
          {items.length === 0 ? (
            <p className="text-center text-sm text-gray-400 py-8">감지된 누락 항목이 없습니다.</p>
          ) : (
            <>
              {/* 전체 선택 토글 */}
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs text-gray-500">등록할 항목을 선택하세요</span>
                <button
                  onClick={toggleAll}
                  className="text-xs text-blue-600 hover:text-blue-700"
                >
                  {allSelected ? "전체 해제" : "전체 선택"}
                </button>
              </div>

              {/* 항목 목록 */}
              <div className="flex flex-col gap-1.5 max-h-72 overflow-y-auto">
                {items.map((item) => (
                  <label
                    key={item.id}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors",
                      item.selected ? "bg-orange-50" : "bg-gray-50 opacity-60"
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={item.selected}
                      onChange={() => toggleItem(item.id)}
                      className="w-3.5 h-3.5 accent-red-500 shrink-0"
                    />
                    <span className="text-xs text-gray-600 w-20 shrink-0">{item.date.slice(5)}</span>
                    <span className="text-xs text-gray-700 flex-1 truncate">{item.writerName}</span>
                    <span className={cn("text-xs px-2 py-0.5 rounded-full shrink-0", CAT_COLOR[item.category] ?? "bg-gray-100 text-gray-600")}>
                      {item.category} — {item.fieldLabel}
                    </span>
                  </label>
                ))}
              </div>
            </>
          )}
        </div>

        {/* 푸터 */}
        <div className="flex gap-2 px-5 py-4 border-t border-gray-100">
          <button
            onClick={handleRegister}
            disabled={registering || selectedItems.length === 0}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-red-500 text-white rounded-lg text-sm font-semibold hover:bg-red-600 disabled:opacity-40"
          >
            {registering && <Loader2 size={13} className="animate-spin" />}
            선택 항목 등록 ({selectedItems.length}건)
          </button>
          <button
            onClick={onClose}
            disabled={registering}
            className="px-4 py-2 border border-gray-200 text-gray-600 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-40"
          >
            취소
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 타입 체크**

```bash
cd /c/git-project/arisa_internal_tool/.worktrees/feature/bulk-eval-modal/frontend && node_modules/.bin/tsc --noEmit
```

오류 없음 확인.

- [ ] **Step 3: 커밋**

```bash
cd /c/git-project/arisa_internal_tool/.worktrees/feature/bulk-eval-modal
git add frontend/src/components/BulkEvalModal.tsx
git commit -m "feat: BulkEvalModal 컴포넌트 구현 (누락 감지 + 체크박스 + 일괄 등록)"
```

---

## Task 3: CareRecordsPage에 버튼 + 모달 연결

**Files:**
- Modify: `frontend/src/pages/CareRecordsPage.tsx`

- [ ] **Step 1: import 추가 및 `users` 쿼리 상단 이동**

파일 상단 import 블록에 추가:
```typescript
import BulkEvalModal from "@/components/BulkEvalModal";
```

`export default function CareRecordsPage()` 내부 state 선언부에 추가 (기존 state 선언들 아래):
```typescript
const [showBulkModal, setShowBulkModal] = useState(false);
```

기존에 `EmployeeEvalForm` 내부에만 있던 `users` 쿼리를 `CareRecordsPage` 본체로 이동:
```typescript
const { data: users = [] } = useQuery({
  queryKey: ["employee-eval-users"],
  queryFn: employeeEvaluationsApi.users,
});
```

- [ ] **Step 2: 탭 행에 버튼 추가**

기존 탭 행 코드를 찾아 버튼을 추가한다.

기존 (line ~212):
```tsx
<div className="flex gap-2">
  {[{ key: "weekly" as MainTab, label: "주간상태변화 평가" }, { key: "daily" as MainTab, label: "일일 특이사항 평가" }].map((t) => (
    <button key={t.key} onClick={() => setActiveTab(t.key)}
      className={cn("px-4 py-2 rounded-lg text-sm font-medium transition-colors",
        activeTab === t.key ? "bg-blue-600 text-white" : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
      )}>
      {t.label}
    </button>
  ))}
</div>
```

변경 후:
```tsx
<div className="flex items-center gap-2">
  {[{ key: "weekly" as MainTab, label: "주간상태변화 평가" }, { key: "daily" as MainTab, label: "일일 특이사항 평가" }].map((t) => (
    <button key={t.key} onClick={() => setActiveTab(t.key)}
      className={cn("px-4 py-2 rounded-lg text-sm font-medium transition-colors",
        activeTab === t.key ? "bg-blue-600 text-white" : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
      )}>
      {t.label}
    </button>
  ))}
  <button
    onClick={() => setShowBulkModal(true)}
    disabled={checkResults.every((r) =>
      (["basic","physical","cognitive","nursing","recovery"] as const).every((cat) =>
        Object.entries(r[cat] as Record<string, boolean | null | string>)
          .every(([k, v]) => k === "writer" || v !== false)
      )
    )}
    className="flex items-center gap-1.5 px-3 py-2 bg-amber-50 text-amber-700 border border-amber-200 rounded-lg text-sm font-medium hover:bg-amber-100 disabled:opacity-40 disabled:cursor-not-allowed"
  >
    ⚠ 누락 일괄 확인
  </button>
</div>
```

- [ ] **Step 3: 모달 마운트 + `EmployeeEvalForm`에서 users prop 제거**

`return` JSX의 최상위 `<div className="space-y-4">` 바로 안쪽 첫 자식으로 추가:
```tsx
<BulkEvalModal
  open={showBulkModal}
  onClose={() => setShowBulkModal(false)}
  records={records}
  users={users}
/>
```

기존 `EmployeeEvalForm`은 내부에서 `useQuery`로 users를 직접 조회했으므로, `CareRecordsPage`로 이동한 쿼리와 캐시 키(`"employee-eval-users"`)가 동일하여 중복 호출 없이 캐시 공유된다. `EmployeeEvalForm` 내부 `useQuery` 선언은 그대로 유지해도 되고 제거해도 된다 (React Query가 중복 방지).

- [ ] **Step 4: 타입 체크**

```bash
cd /c/git-project/arisa_internal_tool/.worktrees/feature/bulk-eval-modal/frontend && node_modules/.bin/tsc --noEmit
```

오류 없음 확인.

- [ ] **Step 5: 커밋**

```bash
cd /c/git-project/arisa_internal_tool/.worktrees/feature/bulk-eval-modal
git add frontend/src/pages/CareRecordsPage.tsx
git commit -m "feat: 일일 탭 옆 누락 일괄 확인 버튼 + BulkEvalModal 연결"
```

---

## Task 4: 최종 검증

- [ ] **Step 1: 전체 타입 체크**

```bash
cd /c/git-project/arisa_internal_tool/.worktrees/feature/bulk-eval-modal/frontend && node_modules/.bin/tsc --noEmit
```

오류 없음 확인.

- [ ] **Step 2: 백엔드 테스트**

```bash
cd /c/git-project/arisa_internal_tool/.worktrees/feature/bulk-eval-modal && pytest tests/backend/ -q --tb=no
```

220 passed 확인 (백엔드 변경 없으므로 동일).

- [ ] **Step 3: 브라우저 동작 확인**

1. 프론트엔드가 실행 중인지 확인 (기존 `npm run dev` 유지)
2. 수급자 선택 → 일일 특이사항 평가 탭
3. `⚠ 누락 일괄 확인` 버튼 클릭 → 모달 열림
4. 누락 항목 목록 확인, 체크박스 개별 선택/해제
5. 전체 선택/해제 토글 동작 확인
6. 선택 항목 등록 버튼 → 성공 toast 확인
7. 누락 항목이 없을 때 버튼 비활성화 확인
