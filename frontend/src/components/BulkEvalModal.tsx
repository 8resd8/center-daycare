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

// ── 필드 → (카테고리) 매핑 ──────────────────────────
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
