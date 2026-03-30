import { useState } from "react";
import { X, Save, Loader2 } from "lucide-react";

interface UploadedDoc {
  file_id: string;
  filename: string;
  total_records: number;
  customer_names: string[];
  records: Record<string, unknown>[];
  saved: boolean;
}

interface Props {
  doc: UploadedDoc;
  onClose: () => void;
  onSave: (file_id: string) => Promise<void>;
  saving: boolean;
}

/** 수급자별 기록 그룹화 */
function groupByCustomer(
  records: Record<string, unknown>[]
): Record<string, Record<string, unknown>[]> {
  const groups: Record<string, Record<string, unknown>[]> = {};
  for (const r of records) {
    const name = (r.customer_name as string) || "미상";
    if (!groups[name]) groups[name] = [];
    groups[name].push(r);
  }
  return groups;
}

export default function UploadPreviewModal({ doc, onClose, onSave, saving }: Props) {
  const [activeCustomer, setActiveCustomer] = useState<string>(
    doc.customer_names[0] ?? ""
  );
  const groups = groupByCustomer(doc.records);
  const customerList = Object.keys(groups).sort();
  const rows = groups[activeCustomer] ?? [];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl mx-4 flex flex-col max-h-[85vh]">
        {/* 헤더 */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div>
            <p className="text-sm font-semibold text-gray-800 truncate max-w-xs">
              {doc.filename}
            </p>
            <p className="text-xs text-gray-400 mt-0.5">
              총 {doc.total_records}건 · {customerList.length}명
            </p>
          </div>
          <div className="flex items-center gap-2">
            {!doc.saved && (
              <button
                onClick={() => onSave(doc.file_id)}
                disabled={saving}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : (
                  <Save size={12} />
                )}
                DB 저장
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* 수급자 탭 */}
        <div className="flex gap-1 px-5 pt-3 pb-0 overflow-x-auto border-b border-gray-100">
          {customerList.map((name) => (
            <button
              key={name}
              onClick={() => setActiveCustomer(name)}
              className={`px-3 py-1.5 text-xs font-medium rounded-t-lg whitespace-nowrap transition-colors ${
                activeCustomer === name
                  ? "bg-blue-600 text-white"
                  : "text-gray-500 hover:bg-gray-100"
              }`}
            >
              {name}
              <span className="ml-1 opacity-70">({groups[name].length})</span>
            </button>
          ))}
        </div>

        {/* 기록 테이블 */}
        <div className="overflow-auto flex-1 px-5 py-3">
          {rows.length === 0 ? (
            <p className="text-xs text-gray-400 text-center py-8">기록 없음</p>
          ) : (
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-gray-50 text-gray-500">
                  <th className="text-left px-2 py-1.5 border border-gray-100 whitespace-nowrap">날짜</th>
                  <th className="text-center px-2 py-1.5 border border-gray-100 whitespace-nowrap">출결</th>
                  <th className="text-center px-2 py-1.5 border border-gray-100 whitespace-nowrap">목욕</th>
                  <th className="text-center px-2 py-1.5 border border-gray-100 whitespace-nowrap">식사(조/중/석)</th>
                  <th className="text-left px-2 py-1.5 border border-gray-100">신체특이사항</th>
                  <th className="text-left px-2 py-1.5 border border-gray-100">인지특이사항</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => {
                  const absent = String(r.total_service_time ?? "").includes("결석") ||
                    String(r.total_service_time ?? "") === "0분";
                  return (
                    <tr key={i} className={i % 2 === 0 ? "bg-white" : "bg-gray-50/50"}>
                      <td className="px-2 py-1 border border-gray-100 whitespace-nowrap font-medium text-gray-700">
                        {String(r.date ?? "")}
                      </td>
                      <td className="px-2 py-1 border border-gray-100 text-center">
                        {absent ? (
                          <span className="text-red-400">결석</span>
                        ) : (
                          <span className="text-green-600">출석</span>
                        )}
                      </td>
                      <td className="px-2 py-1 border border-gray-100 text-center whitespace-nowrap">
                        {String(r.bath_time ?? "-")}
                      </td>
                      <td className="px-2 py-1 border border-gray-100 text-center whitespace-nowrap">
                        {[r.meal_breakfast, r.meal_lunch, r.meal_dinner]
                          .map((v) => (v ? "✓" : "-"))
                          .join(" / ")}
                      </td>
                      <td className="px-2 py-1 border border-gray-100 max-w-[160px] truncate text-gray-600">
                        {String(r.physical_note ?? "")}
                      </td>
                      <td className="px-2 py-1 border border-gray-100 max-w-[160px] truncate text-gray-600">
                        {String(r.cognitive_note ?? "")}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
