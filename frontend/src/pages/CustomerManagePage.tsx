import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Plus, Trash2, Save, Search, Loader2, Pencil, X } from "lucide-react";
import { customersApi } from "@/api/customers";
import type { Customer } from "@/types";

type EditingCustomer = Omit<Customer, "customer_id"> & { customer_id?: number; isNew?: boolean };

export default function CustomerManagePage() {
  const queryClient = useQueryClient();
  const [keyword, setKeyword] = useState("");
  const [editing, setEditing] = useState<EditingCustomer | null>(null);
  const [editingId, setEditingId] = useState<number | null | "new">(null);

  const { data: customers = [], isLoading } = useQuery({
    queryKey: ["customers", keyword],
    queryFn: () => customersApi.list(keyword || undefined),
  });

  const createMutation = useMutation({
    mutationFn: (data: Omit<Customer, "customer_id">) =>
      customersApi.create(data),
    onSuccess: () => {
      toast.success("수급자가 등록되었습니다.");
      queryClient.invalidateQueries({ queryKey: ["customers"] });
      setEditingId(null);
      setEditing(null);
    },
    onError: () => toast.error("등록 실패"),
  });

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: number;
      data: Omit<Customer, "customer_id">;
    }) => customersApi.update(id, data),
    onSuccess: () => {
      toast.success("수정되었습니다.");
      queryClient.invalidateQueries({ queryKey: ["customers"] });
      setEditingId(null);
      setEditing(null);
    },
    onError: () => toast.error("수정 실패"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => customersApi.delete(id),
    onSuccess: () => {
      toast.success("삭제되었습니다.");
      queryClient.invalidateQueries({ queryKey: ["customers"] });
    },
    onError: () => toast.error("삭제 실패"),
  });

  const handleStartEdit = (customer: Customer) => {
    setEditingId(customer.customer_id);
    setEditing({ ...customer });
  };

  const handleStartNew = () => {
    setEditingId("new");
    setEditing({
      name: "",
      birth_date: null,
      gender: null,
      recognition_no: null,
      benefit_start_date: null,
      grade: null,
    });
  };

  const handleSave = () => {
    if (!editing || !editing.name.trim()) {
      toast.error("성명은 필수입니다.");
      return;
    }
    const payload = {
      name: editing.name,
      birth_date: editing.birth_date,
      gender: editing.gender,
      recognition_no: editing.recognition_no,
      benefit_start_date: editing.benefit_start_date,
      grade: editing.grade,
    };

    if (editingId === "new") {
      createMutation.mutate(payload);
    } else if (typeof editingId === "number") {
      updateMutation.mutate({ id: editingId, data: payload });
    }
  };

  const handleDelete = (id: number, name: string) => {
    if (!confirm(`${name} 수급자를 삭제하시겠습니까?`)) return;
    deleteMutation.mutate(id);
  };

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-800">수급자 관리</h1>
        <button
          onClick={handleStartNew}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
        >
          <Plus size={16} />
          수급자 추가
        </button>
      </div>

      {/* 검색 */}
      <div className="relative mb-4">
        <Search
          size={16}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
        />
        <input
          type="text"
          placeholder="이름, 수급자번호 검색"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
        />
      </div>

      {/* 신규 추가 폼 */}
      {editingId === "new" && editing && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-4">
          <h3 className="text-sm font-semibold text-blue-700 mb-3">
            신규 수급자 등록
          </h3>
          <CustomerForm
            data={editing}
            onChange={setEditing}
            onSave={handleSave}
            onCancel={() => {
              setEditingId(null);
              setEditing(null);
            }}
            isSaving={isSaving}
          />
        </div>
      )}

      {/* 테이블 */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 size={24} className="animate-spin text-gray-400" />
          </div>
        ) : customers.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            검색 결과가 없습니다.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {[
                  "성명",
                  "생년월일",
                  "성별",
                  "수급자번호",
                  "급여시작일",
                  "등급",
                  "관리",
                ].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {customers.map((c) =>
                editingId === c.customer_id && editing ? (
                  <tr key={c.customer_id} className="bg-yellow-50">
                    <td colSpan={7} className="px-4 py-3">
                      <CustomerForm
                        data={editing}
                        onChange={setEditing}
                        onSave={handleSave}
                        onCancel={() => {
                          setEditingId(null);
                          setEditing(null);
                        }}
                        isSaving={isSaving}
                      />
                    </td>
                  </tr>
                ) : (
                  <tr
                    key={c.customer_id}
                    className="hover:bg-gray-50 transition-colors"
                  >
                    <td className="px-4 py-3 font-medium text-gray-800">
                      {c.name}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {c.birth_date || "-"}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {c.gender || "-"}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {c.recognition_no || "-"}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {c.benefit_start_date || "-"}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {c.grade || "-"}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleStartEdit(c)}
                          className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded"
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          onClick={() =>
                            handleDelete(c.customer_id, c.name)
                          }
                          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              )}
            </tbody>
          </table>
        )}
      </div>

      <p className="text-xs text-gray-400 mt-2">
        총 {customers.length}명
      </p>
    </div>
  );
}

// ── 수급자 폼 ─────────────────────────────────────────────────
interface CustomerFormProps {
  data: Omit<Customer, "customer_id"> & { customer_id?: number };
  onChange: (data: CustomerFormProps["data"]) => void;
  onSave: () => void;
  onCancel: () => void;
  isSaving: boolean;
}

function CustomerForm({ data, onChange, onSave, onCancel, isSaving }: CustomerFormProps) {
  const update = (field: keyof typeof data, value: string | null) =>
    onChange({ ...data, [field]: value || null });

  return (
    <div className="grid grid-cols-3 gap-3">
      <div>
        <label className="text-xs font-medium text-gray-600">성명 *</label>
        <input
          type="text"
          value={data.name}
          onChange={(e) => update("name", e.target.value)}
          className="mt-1 w-full border border-gray-200 rounded px-2 py-1.5 text-sm"
        />
      </div>
      <div>
        <label className="text-xs font-medium text-gray-600">생년월일</label>
        <input
          type="date"
          value={data.birth_date ?? ""}
          onChange={(e) => update("birth_date", e.target.value)}
          className="mt-1 w-full border border-gray-200 rounded px-2 py-1.5 text-sm"
        />
      </div>
      <div>
        <label className="text-xs font-medium text-gray-600">성별</label>
        <select
          value={data.gender ?? ""}
          onChange={(e) => update("gender", e.target.value)}
          className="mt-1 w-full border border-gray-200 rounded px-2 py-1.5 text-sm"
        >
          <option value="">선택</option>
          <option value="남">남</option>
          <option value="여">여</option>
        </select>
      </div>
      <div>
        <label className="text-xs font-medium text-gray-600">수급자번호</label>
        <input
          type="text"
          value={data.recognition_no ?? ""}
          onChange={(e) => update("recognition_no", e.target.value)}
          className="mt-1 w-full border border-gray-200 rounded px-2 py-1.5 text-sm"
        />
      </div>
      <div>
        <label className="text-xs font-medium text-gray-600">급여시작일</label>
        <input
          type="date"
          value={data.benefit_start_date ?? ""}
          onChange={(e) => update("benefit_start_date", e.target.value)}
          className="mt-1 w-full border border-gray-200 rounded px-2 py-1.5 text-sm"
        />
      </div>
      <div>
        <label className="text-xs font-medium text-gray-600">등급</label>
        <select
          value={data.grade ?? ""}
          onChange={(e) => update("grade", e.target.value)}
          className="mt-1 w-full border border-gray-200 rounded px-2 py-1.5 text-sm"
        >
          <option value="">선택</option>
          {["1등급", "2등급", "3등급", "4등급", "5등급", "인지지원등급"].map(
            (g) => (
              <option key={g} value={g}>
                {g}
              </option>
            )
          )}
        </select>
      </div>
      <div className="col-span-3 flex gap-2">
        <button
          onClick={onSave}
          disabled={isSaving}
          className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          {isSaving ? (
            <Loader2 size={12} className="animate-spin" />
          ) : (
            <Save size={12} />
          )}
          저장
        </button>
        <button
          onClick={onCancel}
          className="flex items-center gap-1 px-3 py-1.5 border border-gray-200 text-gray-600 rounded text-sm hover:bg-gray-50"
        >
          <X size={12} />
          취소
        </button>
      </div>
    </div>
  );
}
