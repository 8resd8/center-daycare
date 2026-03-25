import { useCallback, useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { useDropzone } from "react-dropzone";
import { toast } from "sonner";
import { useQueryClient, useQuery } from "@tanstack/react-query";
import {
  Users,
  UserCheck,
  BarChart3,
  Upload,
  FileText,
  Loader2,
  Check,
  X,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useDocumentStore } from "@/store/documentStore";
import { useFilterStore } from "@/store/filterStore";
import { uploadApi } from "@/api/upload";
import { dailyRecordsApi } from "@/api/dailyRecords";
import { useAuthStore } from "@/store/authStore";
import { authApi } from "@/api/auth";

const navItems = [
  { to: "/", label: "기록지 처리", icon: FileText },
  { to: "/customers", label: "수급자 관리", icon: Users },
  { to: "/employees", label: "직원 관리", icon: UserCheck },
  { to: "/dashboard", label: "대시보드", icon: BarChart3 },
];

interface SidebarProps {
  onClose?: () => void;
}

export default function Sidebar({ onClose }: SidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const isRecordsPage = location.pathname === "/";
  const { user, clearAuth } = useAuthStore();

  const { addDoc, markSaved, uploadedDocs } = useDocumentStore();
  const {
    startDate, endDate,
    setDateRange, setThisMonth, setLastMonth,
    selectedCustomerId, setSelectedCustomerId,
  } = useFilterStore();
  const queryClient = useQueryClient();
  const [localStart, setLocalStart] = useState<string>(startDate ?? "");
  const [localEnd, setLocalEnd] = useState<string>(endDate ?? "");
  const [uploading, setUploading] = useState(false);
  const [savingId, setSavingId] = useState<string | null>(null);

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } finally {
      clearAuth();
      navigate("/login", { replace: true });
    }
  };

  // 수급자 목록 (기록지 처리 페이지에서만 로드)
  const { data: customersWithRecords = [], isLoading: loadingCustomers } = useQuery({
    queryKey: ["customers-with-records", startDate, endDate],
    queryFn: () =>
      dailyRecordsApi.customersWithRecords({
        start_date: startDate ?? undefined,
        end_date: endDate ?? undefined,
      }),
    enabled: isRecordsPage,
  });

  const handleThisMonth = () => {
    setThisMonth();
    const store = useFilterStore.getState();
    setLocalStart(store.startDate ?? "");
    setLocalEnd(store.endDate ?? "");
  };

  const handleLastMonth = () => {
    setLastMonth();
    const store = useFilterStore.getState();
    setLocalStart(store.startDate ?? "");
    setLocalEnd(store.endDate ?? "");
  };

  const handleSearch = () => {
    setDateRange(localStart || null, localEnd || null);
  };

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      let firstCustomerNames: string[] = [];
      for (const file of acceptedFiles) {
        if (!file.name.toLowerCase().endsWith(".pdf")) {
          toast.error(`${file.name}: PDF 파일만 업로드 가능합니다.`);
          continue;
        }
        setUploading(true);
        try {
          const result = await uploadApi.upload(file);
          await uploadApi.save(result.file_id);
          addDoc(result);
          markSaved(result.file_id);
          if (firstCustomerNames.length === 0) firstCustomerNames = result.customer_names;
          toast.success(`${file.name} 저장 완료 (${result.total_records}건)`);
        } catch {
          toast.error(`${file.name} 업로드 실패`);
        } finally {
          setUploading(false);
        }
      }
      // 업로드 완료 후 목록 갱신 + 첫 번째 수급자 자동 선택
      if (firstCustomerNames.length > 0) {
        const { startDate: sd, endDate: ed, setSelectedCustomerId: setSel } = useFilterStore.getState();
        try {
          const freshList = await queryClient.fetchQuery({
            queryKey: ["customers-with-records", sd, ed],
            queryFn: () => dailyRecordsApi.customersWithRecords({
              start_date: sd ?? undefined,
              end_date: ed ?? undefined,
            }),
            staleTime: 0,
          });
          const match = freshList.find((c) => firstCustomerNames.includes(c.name));
          if (match) setSel(match.customer_id);
        } catch {
          await queryClient.invalidateQueries({ queryKey: ["customers-with-records"] });
        }
      }
    },
    [addDoc, markSaved, queryClient]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    multiple: true,
  });

  const handleSave = async (file_id: string) => {
    setSavingId(file_id);
    try {
      const res = await uploadApi.save(file_id);
      markSaved(file_id);
      await queryClient.invalidateQueries({ queryKey: ["customers-with-records"] });
      toast.success(res.message);
    } catch {
      toast.error("DB 저장 실패");
    } finally {
      setSavingId(null);
    }
  };

  return (
    <aside className="w-[240px] flex-shrink-0 bg-white border-r border-gray-200 flex flex-col overflow-y-auto">
      {/* 로고 */}
      <div className="px-4 py-5 border-b border-gray-100 flex items-start justify-between">
        <div>
          <h1 className="text-base font-bold text-blue-700 leading-tight">
            보은사랑
            <br />
            <span className="text-xs font-normal text-gray-500">업무 관리 시스템</span>
          </h1>
          {user && (
            <p className="text-xs text-gray-400 mt-1">{user.name}</p>
          )}
        </div>
        {onClose && (
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 text-gray-400">
            <X size={16} />
          </button>
        )}
      </div>

      {/* 네비게이션 */}
      <nav className="px-3 py-3 space-y-1 border-b border-gray-100">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              )
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* 날짜 필터 */}
      <div className="px-4 py-3 border-b border-gray-100">
        <p className="text-xs font-medium text-gray-500 mb-2">날짜 필터</p>
        <div className="flex gap-1 mb-2">
          <button onClick={handleThisMonth} className="text-xs px-2 py-1 rounded border border-gray-200 hover:bg-gray-50">이번달</button>
          <button onClick={handleLastMonth} className="text-xs px-2 py-1 rounded border border-gray-200 hover:bg-gray-50">지난달</button>
        </div>
        <div className="space-y-1">
          <input type="date" value={localStart} onChange={(e) => setLocalStart(e.target.value)} className="w-full text-xs border border-gray-200 rounded px-2 py-1" />
          <input type="date" value={localEnd} onChange={(e) => setLocalEnd(e.target.value)} className="w-full text-xs border border-gray-200 rounded px-2 py-1" />
        </div>
        <button onClick={handleSearch} className="mt-2 w-full text-xs bg-blue-600 text-white rounded py-1.5 hover:bg-blue-700">
          조회
        </button>
      </div>

      {/* 수급자 목록 (기록지 처리 페이지) */}
      {isRecordsPage && (
        <div className="px-4 py-3 border-b border-gray-100 flex-1 overflow-y-auto">
          <p className="text-xs font-medium text-gray-500 mb-2">
            수급자 목록
            {startDate && endDate && (
              <span className="text-gray-400 font-normal ml-1">({startDate?.slice(5)} ~ {endDate?.slice(5)})</span>
            )}
          </p>
          {loadingCustomers ? (
            <div className="flex justify-center py-3">
              <Loader2 size={16} className="animate-spin text-gray-400" />
            </div>
          ) : customersWithRecords.length === 0 ? (
            <p className="text-xs text-gray-400 text-center py-3">기록 없음</p>
          ) : (
            <div className="space-y-0.5">
              {customersWithRecords.map((c) => (
                <button
                  key={c.customer_id}
                  onClick={() => setSelectedCustomerId(c.customer_id)}
                  className={cn(
                    "w-full text-left px-2 py-1.5 rounded-lg text-xs transition-colors",
                    selectedCustomerId === c.customer_id
                      ? "bg-blue-50 text-blue-700 font-medium"
                      : "text-gray-600 hover:bg-gray-100"
                  )}
                >
                  <span className="font-medium">{c.name}</span>
                  <span className="text-gray-400 ml-1">({c.record_count}건)</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* PDF 업로드 */}
      <div className="px-4 py-3 border-b border-gray-100">
        <p className="text-xs font-medium text-gray-500 mb-2">PDF 업로드</p>
        <div
          {...getRootProps()}
          className={cn(
            "border-2 border-dashed rounded-lg p-3 text-center cursor-pointer transition-colors text-xs",
            isDragActive
              ? "border-blue-400 bg-blue-50 text-blue-600"
              : "border-gray-300 text-gray-400 hover:border-blue-300 hover:text-blue-500"
          )}
        >
          <input {...getInputProps()} />
          {uploading ? (
            <div className="flex items-center justify-center gap-1">
              <Loader2 size={14} className="animate-spin" />
              파싱 중...
            </div>
          ) : isDragActive ? (
            <p>여기에 놓으세요</p>
          ) : (
            <div>
              <Upload size={20} className="mx-auto mb-1 text-gray-300" />
              <p>PDF 드래그 또는 클릭</p>
            </div>
          )}
        </div>
      </div>

      {/* 업로드된 파일 목록 */}
      {uploadedDocs.length > 0 && (
        <div className="px-4 py-3">
          <p className="text-xs font-medium text-gray-500 mb-2">업로드 파일</p>
          <div className="space-y-2">
            {uploadedDocs.map((doc) => (
              <div key={doc.file_id} className="bg-gray-50 rounded p-2 text-xs">
                <p className="font-medium text-gray-700 truncate">{doc.filename}</p>
                <p className="text-gray-400">
                  {doc.customer_names.slice(0, 3).join(", ")}
                  {doc.customer_names.length > 3 && ` 외 ${doc.customer_names.length - 3}명`}
                </p>
                <p className="text-gray-400">{doc.total_records}건</p>
                {doc.saved ? (
                  <div className="flex items-center gap-1 mt-1 text-green-600">
                    <Check size={12} /><span>저장 완료</span>
                  </div>
                ) : (
                  <button
                    onClick={() => handleSave(doc.file_id)}
                    disabled={savingId === doc.file_id}
                    className="mt-1 w-full text-xs bg-blue-600 text-white rounded py-1 hover:bg-blue-700 disabled:opacity-50"
                  >
                    {savingId === doc.file_id ? <Loader2 size={12} className="animate-spin mx-auto" /> : "DB 저장"}
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      {/* 로그아웃 */}
      <div className="px-4 py-3 border-t border-gray-100 mt-auto">
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-xs text-gray-500 hover:bg-gray-50 hover:text-gray-800 transition-colors"
        >
          <LogOut size={14} />
          로그아웃
        </button>
      </div>
    </aside>
  );
}
