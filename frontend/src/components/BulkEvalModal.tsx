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
