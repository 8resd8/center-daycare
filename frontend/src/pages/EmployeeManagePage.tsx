import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Plus, Trash2, Save, Search, Loader2, Pencil, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { employeesApi } from "@/api/employees";
import type { Employee } from "@/types";

const WORK_STATUS_OPTIONS = ["재직", "퇴사", "휴직", "전체"];
const JOB_TYPE_OPTIONS = [
  "요양보호사",
  "간호사",
  "간호조무사",
  "사회복지사",
  "물리치료사",
  "작업치료사",
  "영양사",
  "조리사",
  "",
];

type EditingEmployee = Omit<Employee, "user_id"> & {
  user_id?: number;
  username?: string;
  password?: string;
};

export default function EmployeeManagePage() {
  const queryClient = useQueryClient();
  const [keyword, setKeyword] = useState("");
  const [workStatus, setWorkStatus] = useState("재직");
  const [editingId, setEditingId] = useState<number | null | "new">(null);
  const [editing, setEditing] = useState<EditingEmployee | null>(null);

  const { data: employees = [], isLoading } = useQuery({
    queryKey: ["employees", keyword, workStatus],
    queryFn: () =>
      employeesApi.list({
        keyword: keyword || undefined,
        work_status: workStatus !== "전체" ? workStatus : undefined,
      }),
  });

  const createMutation = useMutation({
    mutationFn: (data: EditingEmployee & { username: string; password: string }) =>
      employeesApi.create(data),
    onSuccess: () => {
      toast.success("직원이 등록되었습니다.");
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      setEditingId(null);
      setEditing(null);
    },
    onError: () => toast.error("등록 실패"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Omit<Employee, "user_id"> }) =>
      employeesApi.update(id, data),
    onSuccess: () => {
      toast.success("수정되었습니다.");
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      setEditingId(null);
      setEditing(null);
    },
    onError: () => toast.error("수정 실패"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => employeesApi.softDelete(id),
    onSuccess: () => {
      toast.success("퇴사 처리되었습니다.");
      queryClient.invalidateQueries({ queryKey: ["employees"] });
    },
    onError: () => toast.error("처리 실패"),
  });

  const handleStartEdit = (emp: Employee) => {
    setEditingId(emp.user_id);
    setEditing({ ...emp });
  };

  const handleStartNew = () => {
    setEditingId("new");
    setEditing({
      name: "",
      gender: null,
      birth_date: null,
      work_status: "재직",
      job_type: null,
      hire_date: null,
      resignation_date: null,
      license_name: null,
      license_date: null,
      username: "",
      password: "",
    });
  };

  const handleSave = () => {
    if (!editing || !editing.name.trim()) {
      toast.error("성명은 필수입니다.");
      return;
    }

    const payload = {
      name: editing.name,
      gender: editing.gender,
      birth_date: editing.birth_date,
      work_status: editing.work_status,
      job_type: editing.job_type,
      hire_date: editing.hire_date,
      resignation_date: editing.resignation_date,
      license_name: editing.license_name,
      license_date: editing.license_date,
    };

    if (editingId === "new") {
      if (!editing.username || !editing.password) {
        toast.error("아이디와 비밀번호는 필수입니다.");
        return;
      }
      createMutation.mutate({
        ...payload,
        username: editing.username!,
        password: editing.password!,
      });
    } else if (typeof editingId === "number") {
      updateMutation.mutate({ id: editingId, data: payload });
    }
  };

  const handleSoftDelete = (emp: Employee) => {
    if (!confirm(`${emp.name} 직원을 퇴사 처리하시겠습니까?`)) return;
    deleteMutation.mutate(emp.user_id);
  };

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-800">직원 관리</h1>
        <button
          onClick={handleStartNew}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
        >
          <Plus size={16} />
          직원 추가
        </button>
      </div>

      {/* 검색 + 필터 */}
      <div className="flex gap-3 mb-4">
        <div className="relative flex-1">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
          />
          <input
            type="text"
            placeholder="이름, 직종 검색"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
          />
        </div>
        <div className="flex gap-1">
          {WORK_STATUS_OPTIONS.map((s) => (
            <button
              key={s}
              onClick={() => setWorkStatus(s)}
              className={cn(
                "px-3 py-2 rounded-lg text-sm border transition-colors",
                workStatus === s
                  ? "bg-blue-600 text-white border-blue-600"
                  : "border-gray-200 text-gray-600 hover:bg-gray-50"
              )}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* 신규 추가 폼 */}
      {editingId === "new" && editing && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-4">
          <h3 className="text-sm font-semibold text-blue-700 mb-3">
            신규 직원 등록
          </h3>
          <EmployeeForm
            data={editing}
            onChange={setEditing}
            onSave={handleSave}
            onCancel={() => {
              setEditingId(null);
              setEditing(null);
            }}
            isSaving={isSaving}
            isNew
          />
        </div>
      )}

      {/* 테이블 */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 size={24} className="animate-spin text-gray-400" />
          </div>
        ) : employees.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            직원이 없습니다.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {["성명", "성별", "생년월일", "직종", "근무상태", "입사일", "자격증", "관리"].map(
                  (h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500"
                    >
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {employees.map((emp) =>
                editingId === emp.user_id && editing ? (
                  <tr key={emp.user_id} className="bg-yellow-50">
                    <td colSpan={8} className="px-4 py-3">
                      <EmployeeForm
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
                    key={emp.user_id}
                    className="hover:bg-gray-50 transition-colors"
                  >
                    <td className="px-4 py-3 font-medium text-gray-800">
                      {emp.name}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {emp.gender || "-"}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {emp.birth_date || "-"}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {emp.job_type || "-"}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          "text-xs px-2 py-0.5 rounded-full",
                          emp.work_status === "재직"
                            ? "bg-green-100 text-green-700"
                            : emp.work_status === "퇴사"
                            ? "bg-red-100 text-red-700"
                            : "bg-gray-100 text-gray-600"
                        )}
                      >
                        {emp.work_status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {emp.hire_date || "-"}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {emp.license_name || "-"}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleStartEdit(emp)}
                          className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded"
                        >
                          <Pencil size={14} />
                        </button>
                        {emp.work_status !== "퇴사" && (
                          <button
                            onClick={() => handleSoftDelete(emp)}
                            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
                            title="퇴사 처리"
                          >
                            <Trash2 size={14} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              )}
            </tbody>
          </table>
        )}
      </div>
      <p className="text-xs text-gray-400 mt-2">총 {employees.length}명</p>
    </div>
  );
}

// ── 직원 폼 ───────────────────────────────────────────────────
interface EmployeeFormProps {
  data: EditingEmployee;
  onChange: (data: EditingEmployee) => void;
  onSave: () => void;
  onCancel: () => void;
  isSaving: boolean;
  isNew?: boolean;
}

function EmployeeForm({
  data,
  onChange,
  onSave,
  onCancel,
  isSaving,
  isNew,
}: EmployeeFormProps) {
  const update = (field: keyof EditingEmployee, value: string | null) =>
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
        <label className="text-xs font-medium text-gray-600">성별</label>
        <select
          value={data.gender ?? ""}
          onChange={(e) => update("gender", e.target.value)}
          className="mt-1 w-full border border-gray-200 rounded px-2 py-1.5 text-sm"
        >
          <option value="">선택</option>
          <option value="남성">남성</option>
          <option value="여성">여성</option>
        </select>
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
        <label className="text-xs font-medium text-gray-600">직종</label>
        <select
          value={data.job_type ?? ""}
          onChange={(e) => update("job_type", e.target.value)}
          className="mt-1 w-full border border-gray-200 rounded px-2 py-1.5 text-sm"
        >
          {JOB_TYPE_OPTIONS.map((j) => (
            <option key={j} value={j}>
              {j || "선택"}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="text-xs font-medium text-gray-600">근무상태</label>
        <select
          value={data.work_status ?? "재직"}
          onChange={(e) => update("work_status", e.target.value)}
          className="mt-1 w-full border border-gray-200 rounded px-2 py-1.5 text-sm"
        >
          {["재직", "퇴사", "휴직"].map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="text-xs font-medium text-gray-600">입사일</label>
        <input
          type="date"
          value={data.hire_date ?? ""}
          onChange={(e) => update("hire_date", e.target.value)}
          className="mt-1 w-full border border-gray-200 rounded px-2 py-1.5 text-sm"
        />
      </div>
      <div>
        <label className="text-xs font-medium text-gray-600">자격증명</label>
        <input
          type="text"
          value={data.license_name ?? ""}
          onChange={(e) => update("license_name", e.target.value)}
          className="mt-1 w-full border border-gray-200 rounded px-2 py-1.5 text-sm"
        />
      </div>
      <div>
        <label className="text-xs font-medium text-gray-600">자격증 취득일</label>
        <input
          type="date"
          value={data.license_date ?? ""}
          onChange={(e) => update("license_date", e.target.value)}
          className="mt-1 w-full border border-gray-200 rounded px-2 py-1.5 text-sm"
        />
      </div>

      {isNew && (
        <>
          <div>
            <label className="text-xs font-medium text-gray-600">아이디 *</label>
            <input
              type="text"
              value={data.username ?? ""}
              onChange={(e) => update("username", e.target.value)}
              className="mt-1 w-full border border-gray-200 rounded px-2 py-1.5 text-sm"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600">비밀번호 *</label>
            <input
              type="password"
              value={data.password ?? ""}
              onChange={(e) => update("password", e.target.value)}
              className="mt-1 w-full border border-gray-200 rounded px-2 py-1.5 text-sm"
            />
          </div>
        </>
      )}

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
