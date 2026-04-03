import { useState, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  Cell,
  ResponsiveContainer,
} from "recharts";
import { Loader2, TrendingDown, TrendingUp, Users, FileText, AlertTriangle, Trash2, Plus, Pencil, Check, X } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useFilterStore } from "@/store/filterStore";
import { dashboardApi } from "@/api/dashboard";
import { employeeEvaluationsApi } from "@/api/employeeEvaluations";
import { feedbackReportsApi } from "@/api/feedbackReports";
import type { EmpEvalRankingItem, FeedbackReport, FeedbackReportMonthItem } from "@/types";

type DashTab = "stats" | "rankings" | "details";

// 평가 유형 색상
const EVAL_TYPE_COLORS: Record<string, string> = {
  누락: "#dc2626",
  내용부족: "#f97316",
  오타: "#eab308",
  문법: "#10b981",
  오류: "#8b5cf6",
};

const CATEGORY_OPTIONS = ["공통", "신체", "인지", "간호", "기능"];
const EVAL_TYPE_OPTIONS = ["누락", "내용부족", "오타", "문법", "오류"];

export default function DashboardPage() {
  const { startDate, endDate, setThisMonth, setLastMonth, setDateRange } =
    useFilterStore();
  const [activeTab, setActiveTab] = useState<DashTab>("stats");
  const [selectedEmployee, setSelectedEmployee] =
    useState<EmpEvalRankingItem | null>(null);

  const queryClient = useQueryClient();

  // KPI 요약
  const { data: kpiSummary, isLoading: loadingKpi } = useQuery({
    queryKey: ["dashboard-kpi-summary", startDate, endDate],
    queryFn: () =>
      dashboardApi.kpiSummary(startDate ?? undefined, endDate ?? undefined),
  });

  // 직원 평가 추이
  const { data: empEvalTrend = [] } = useQuery({
    queryKey: ["dashboard-emp-eval-trend", startDate, endDate],
    queryFn: () =>
      dashboardApi.empEvalTrend(startDate ?? undefined, endDate ?? undefined),
  });

  // 직원 평가 카테고리 분포
  const { data: empEvalCategory = [] } = useQuery({
    queryKey: ["dashboard-emp-eval-category", startDate, endDate],
    queryFn: () =>
      dashboardApi.empEvalCategory(startDate ?? undefined, endDate ?? undefined),
  });

  // 직원 평가 랭킹
  const { data: empEvalRankings = [] } = useQuery({
    queryKey: ["dashboard-emp-eval-rankings", startDate, endDate],
    queryFn: () =>
      dashboardApi.empEvalRankings(startDate ?? undefined, endDate ?? undefined),
  });

  // 기간 비교
  const { data: periodComparison } = useQuery({
    queryKey: ["dashboard-period-comparison", startDate, endDate],
    queryFn: () =>
      dashboardApi.periodComparison(startDate ?? undefined, endDate ?? undefined),
  });

  // 직원 개별 평가 이력
  const { data: empEvalHistory, isLoading: loadingHistory } = useQuery({
    queryKey: ["dashboard-emp-eval-history", selectedEmployee?.user_id, startDate, endDate],
    queryFn: () =>
      dashboardApi.empEvalHistory(
        selectedEmployee!.user_id,
        startDate ?? undefined,
        endDate ?? undefined
      ),
    enabled: !!selectedEmployee,
  });

  // 직원별 월별 추이
  const { data: monthlyTrend = [] } = useQuery({
    queryKey: ["dashboard-employee-monthly-trend", selectedEmployee?.user_id],
    queryFn: () =>
      dashboardApi.employeeMonthlyTrend(selectedEmployee!.user_id),
    enabled: !!selectedEmployee,
  });

  // 기간 비교 차트 데이터
  const periodChartData = (() => {
    if (!periodComparison) return [];
    const allTypes = new Set([
      ...Object.keys(periodComparison.current_period.by_type),
      ...Object.keys(periodComparison.previous_period.by_type),
    ]);
    return Array.from(allTypes).map((type) => ({
      type,
      이전: periodComparison.previous_period.by_type[type] ?? 0,
      현재: periodComparison.current_period.by_type[type] ?? 0,
    }));
  })();

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-800">직원 관리 현황</h1>
        {/* 날짜 필터 */}
        <div className="flex items-center gap-2">
          <button
            onClick={setThisMonth}
            className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50"
          >
            이번달
          </button>
          <button
            onClick={setLastMonth}
            className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50"
          >
            지난달
          </button>
          <input
            type="date"
            value={startDate ?? ""}
            onChange={(e) => setDateRange(e.target.value, endDate)}
            className="text-xs border border-gray-200 rounded-lg px-2 py-1.5"
          />
          <span className="text-gray-400">~</span>
          <input
            type="date"
            value={endDate ?? ""}
            onChange={(e) => setDateRange(startDate, e.target.value)}
            className="text-xs border border-gray-200 rounded-lg px-2 py-1.5"
          />
        </div>
      </div>

      {/* KPI 카드 */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {loadingKpi ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="bg-white rounded-xl border border-gray-200 p-4 h-24 animate-pulse"
            />
          ))
        ) : (
          <>
            <KpiCard
              icon={<FileText size={20} />}
              label="총 지적 건수"
              value={`${kpiSummary?.total_issues ?? 0}건`}
              color="blue"
              delta={kpiSummary?.total_issues_delta}
              invertColor
            />
            <KpiCard
              icon={<TrendingDown size={20} />}
              label="직원당 평균 지적"
              value={kpiSummary?.avg_per_employee != null ? `${kpiSummary.avg_per_employee}건` : "-"}
              color="purple"
              delta={kpiSummary?.avg_per_employee_delta}
              invertColor
            />
            <KpiCard
              icon={<AlertTriangle size={20} />}
              label="집중 관리 필요 (5건↑)"
              value={`${kpiSummary?.high_risk_count ?? 0}명`}
              color="yellow"
              subtitle={kpiSummary?.high_risk_count_prev != null ? `이전: ${kpiSummary.high_risk_count_prev}명` : undefined}
            />
            <KpiCard
              icon={<Users size={20} />}
              label="재직 직원"
              value={`${kpiSummary?.total_employees ?? 0}명`}
              color="green"
            />
          </>
        )}
      </div>

      {/* 탭 */}
      <div className="flex gap-2 mb-4">
        {(
          [
            { key: "stats", label: "통계 분석" },
            { key: "rankings", label: "직원별 명단" },
            { key: "details", label: "개별 리포트" },
          ] as { key: DashTab; label: string }[]
        ).map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={cn(
              "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
              activeTab === t.key
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── 탭 1: 통계 분석 ── */}
      {activeTab === "stats" && (
        <div className="space-y-4">
          {/* 평가 추이 선형 차트 */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-700 mb-4">평가 유형별 추이</h3>
            {empEvalTrend.length === 0 ? (
              <div className="text-center py-8 text-gray-400 text-sm">
                직원 평가 데이터 없음
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={empEvalTrend}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip />
                  <Legend />
                  {(["누락", "내용부족", "오타", "문법", "오류"] as const).map((type) => (
                    <Line
                      key={type}
                      type="monotone"
                      dataKey={type}
                      name={type}
                      stroke={EVAL_TYPE_COLORS[type]}
                      strokeWidth={2}
                      dot={{ r: 3 }}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* 카테고리 분포 + 기간 비교 (2열) */}
          <div className="grid grid-cols-2 gap-4">
            {/* 카테고리별 지적 현황 막대 차트 */}
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-700 mb-4">카테고리별 지적 현황</h3>
              {empEvalCategory.length === 0 ? (
                <div className="text-center py-8 text-gray-400 text-sm">데이터 없음</div>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={empEvalCategory} margin={{ bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="category" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="count" name="건수" fill="#3b82f6" radius={[4, 4, 0, 0]}>
                      {empEvalCategory.map((_, i) => (
                        <Cell
                          key={i}
                          fill={["#3b82f6", "#8b5cf6", "#10b981", "#f97316", "#ec4899"][i % 5]}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>

            {/* 기간 비교 막대 차트 */}
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-700 mb-4">기간 비교 (유형별)</h3>
              {periodChartData.length === 0 ? (
                <div className="text-center py-8 text-gray-400 text-sm">
                  날짜를 선택하면 이전 기간과 비교합니다
                </div>
              ) : (
                <>
                  <ResponsiveContainer width="100%" height={190}>
                    <BarChart data={periodChartData} margin={{ bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="type" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="이전" fill="#94a3b8" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="현재" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                  {periodComparison && (
                    <p className="text-xs text-gray-500 mt-2 text-center">
                      이전 {periodComparison.previous_period.total}건 → 현재{" "}
                      {periodComparison.current_period.total}건
                      {periodComparison.change_rate != null && (
                        <span
                          className={cn(
                            "ml-1 font-semibold",
                            periodComparison.change_rate > 0
                              ? "text-red-500"
                              : periodComparison.change_rate < 0
                                ? "text-green-500"
                                : "text-gray-500"
                          )}
                        >
                          ({periodComparison.change_rate > 0 ? "+" : ""}
                          {periodComparison.change_rate}%)
                        </span>
                      )}
                    </p>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── 탭 2: 직원별 명단 ── */}
      {activeTab === "rankings" && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {["순위", "성명", "지적 횟수", "주요 유형"].map((h) => (
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
              {empEvalRankings.map((emp, i) => (
                <tr
                  key={emp.user_id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => {
                    setSelectedEmployee(emp);
                    setActiveTab("details");
                  }}
                >
                  <td className="px-4 py-3 text-gray-500 font-medium">{i + 1}</td>
                  <td className="px-4 py-3 font-medium text-gray-800">{emp.name}</td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        "text-sm font-semibold",
                        emp.total_count >= 5 ? "text-red-600" : emp.total_count >= 3 ? "text-orange-500" : "text-gray-700"
                      )}
                    >
                      {emp.total_count}건
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {emp.main_type !== "-" ? (
                      <span
                        className="text-xs px-2 py-0.5 rounded-full font-medium text-white"
                        style={{ backgroundColor: EVAL_TYPE_COLORS[emp.main_type] ?? "#94a3b8" }}
                      >
                        {emp.main_type}
                      </span>
                    ) : (
                      <span className="text-gray-300 text-xs">-</span>
                    )}
                  </td>
                </tr>
              ))}
              {empEvalRankings.length === 0 && (
                <tr>
                  <td colSpan={4} className="text-center py-8 text-gray-400">
                    데이터 없음
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          <p className="text-xs text-gray-400 px-4 py-2 border-t border-gray-100">
            직원을 클릭하면 개별 리포트를 확인할 수 있습니다.
          </p>
        </div>
      )}

      {/* ── 탭 3: 개별 리포트 ── */}
      {activeTab === "details" && (
        <DetailsTab
          empEvalRankings={empEvalRankings}
          selectedEmployee={selectedEmployee}
          setSelectedEmployee={setSelectedEmployee}
          startDate={startDate}
          endDate={endDate}
          empEvalHistory={empEvalHistory}
          loadingHistory={loadingHistory}
          monthlyTrend={monthlyTrend}
          queryClient={queryClient}
        />
      )}
    </div>
  );
}

// ── AI 피드백 패널 ───────────────────────────────────────────────
function AiFeedbackPanel({ userId }: { userId: number }) {
  const today = new Date();
  const defaultMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;

  const [targetMonth, setTargetMonth] = useState(defaultMonth);
  const [adminNote, setAdminNote] = useState("");
  const [generating, setGenerating] = useState(false);
  const [savedMonths, setSavedMonths] = useState<FeedbackReportMonthItem[]>([]);
  const [currentReport, setCurrentReport] = useState<FeedbackReport | null>(null);
  const [loadingMonths, setLoadingMonths] = useState(false);
  const [loadingReport, setLoadingReport] = useState(false);

  useEffect(() => {
    setCurrentReport(null);
    setSavedMonths([]);
    setLoadingMonths(true);
    feedbackReportsApi
      .listMonths(userId)
      .then(setSavedMonths)
      .catch(() => {})
      .finally(() => setLoadingMonths(false));
  }, [userId]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const report = await feedbackReportsApi.generate(userId, targetMonth, adminNote || null);
      setCurrentReport(report);
      const months = await feedbackReportsApi.listMonths(userId);
      setSavedMonths(months);
      toast.success("AI 피드백이 생성되었습니다.");
    } catch {
      toast.error("피드백 생성 실패");
    } finally {
      setGenerating(false);
    }
  };

  const handleLoadMonth = async (month: string) => {
    setLoadingReport(true);
    try {
      const report = await feedbackReportsApi.getByMonth(userId, month);
      setCurrentReport(report);
    } catch {
      toast.error("피드백 로드 실패");
    } finally {
      setLoadingReport(false);
    }
  };

  const monthOptions: string[] = [];
  for (let i = 0; i < 12; i++) {
    const d = new Date(today.getFullYear(), today.getMonth() - i, 1);
    monthOptions.push(
      `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`
    );
  }

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="font-semibold text-gray-700 mb-3">AI 피드백 생성</h3>
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="text-xs text-gray-500 block mb-1">대상 월</label>
            <select
              value={targetMonth}
              onChange={(e) => setTargetMonth(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
            >
              {monthOptions.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
          <div className="flex-1 min-w-[200px]">
            <label className="text-xs text-gray-500 block mb-1">관리자 메모 (선택)</label>
            <input
              type="text"
              value={adminNote}
              onChange={(e) => setAdminNote(e.target.value)}
              placeholder="AI 참고용 메모 입력"
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="flex items-center gap-2 px-5 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {generating && <Loader2 size={14} className="animate-spin" />}
            AI 피드백 생성
          </button>
        </div>
      </div>

      {loadingMonths ? (
        <div className="flex justify-center py-4">
          <Loader2 size={20} className="animate-spin text-gray-400" />
        </div>
      ) : savedMonths.length > 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs text-gray-500 mb-2">저장된 월</p>
          <div className="flex flex-wrap gap-2">
            {savedMonths.map((item) => (
              <button
                key={item.target_month}
                onClick={() => handleLoadMonth(item.target_month)}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                  currentReport?.target_month === item.target_month
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100"
                }`}
              >
                {item.target_month}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {loadingReport ? (
        <div className="flex justify-center py-8">
          <Loader2 size={24} className="animate-spin text-gray-400" />
        </div>
      ) : currentReport ? (
        <div className="space-y-4">
          {/* ── 강점 + 총평 ── */}
          {(currentReport.ai_result.strengths || currentReport.ai_result.overall_comment) && (
            <div className="bg-green-50 rounded-xl border border-green-200 p-5 space-y-2">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-green-600 font-semibold text-sm">이달의 강점</span>
              </div>
              {currentReport.ai_result.strengths && (
                <p className="text-sm text-green-800 leading-relaxed">
                  {currentReport.ai_result.strengths}
                </p>
              )}
              {currentReport.ai_result.overall_comment && (
                <p className="text-xs text-green-600 mt-1">
                  {currentReport.ai_result.overall_comment}
                </p>
              )}
            </div>
          )}

          {/* ── 지적 사항 테이블 ── */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100">
              <h3 className="font-semibold text-gray-700">
                {currentReport.target_month} 피드백
              </h3>
              {currentReport.admin_note && (
                <p className="text-xs text-gray-400 mt-1">메모: {currentReport.admin_note}</p>
              )}
            </div>
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {["구분", "상세내용", "비고"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {(currentReport.ai_result.summary_table ?? []).map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-xs font-medium text-gray-700 whitespace-nowrap">
                      {row.구분}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-600">{row.상세내용}</td>
                    <td className="px-4 py-3 text-xs text-gray-400 whitespace-nowrap">{row.비고}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* ── 우선 개선 행동 ── */}
          {currentReport.ai_result.priority_actions &&
            currentReport.ai_result.priority_actions.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-100">
                  <h3 className="font-semibold text-gray-700">이번 달 우선 개선 행동</h3>
                </div>
                <div className="divide-y divide-gray-100">
                  {currentReport.ai_result.priority_actions.map((action, i) => (
                    <div key={i} className="px-5 py-4 flex gap-4 items-start">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center">
                        {action.순위}
                      </span>
                      <div className="space-y-1 min-w-0">
                        <p className="text-sm font-semibold text-gray-800">{action.개선_항목}</p>
                        <p className="text-xs text-gray-600">
                          <span className="font-medium text-gray-500">실천 방법: </span>
                          {action.실천_방법}
                        </p>
                        <p className="text-xs text-blue-700 bg-blue-50 rounded px-2 py-1">
                          💙 {action.기대_효과}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

          {/* ── 작성 방식 개선 예시 ── */}
          {(currentReport.ai_result.improvement_examples?.length ?? 0) > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-5 py-4 border-b border-gray-100">
                <h3 className="font-semibold text-gray-700">작성 방식 개선 예시</h3>
              </div>
              <div className="divide-y divide-gray-100">
                {(currentReport.ai_result.improvement_examples ?? []).map((ex, i) => (
                  <div key={i} className="px-5 py-4 space-y-2">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-red-50 rounded-lg px-3 py-2">
                        <p className="text-xs text-red-500 font-medium mb-1">기존</p>
                        <p className="text-xs text-gray-600">{ex.기존_작성방식}</p>
                      </div>
                      <div className="bg-green-50 rounded-lg px-3 py-2">
                        <p className="text-xs text-green-600 font-medium mb-1">개선</p>
                        <p className="text-xs text-gray-800 font-medium">{ex.개선_작성방식}</p>
                      </div>
                    </div>
                    {ex.개선_포인트 && (
                      <p className="text-xs text-gray-500 italic pl-1">
                        ✦ {ex.개선_포인트}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── 자기점검 체크리스트 ── */}
          {currentReport.ai_result.self_checklist &&
            currentReport.ai_result.self_checklist.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <h3 className="font-semibold text-gray-700 mb-3">기록 제출 전 자기점검</h3>
                <ul className="space-y-2">
                  {currentReport.ai_result.self_checklist.map((item, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-gray-700">
                      <span className="flex-shrink-0 w-4 h-4 rounded border border-gray-300 mt-0.5" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400 text-sm">
          대상 월을 선택하고 AI 피드백을 생성하거나, 저장된 월을 클릭하세요.
        </div>
      )}
    </div>
  );
}

// ── 개별 리포트 탭 ───────────────────────────────────────────────
interface DetailsTabProps {
  empEvalRankings: EmpEvalRankingItem[];
  selectedEmployee: EmpEvalRankingItem | null;
  setSelectedEmployee: (e: EmpEvalRankingItem | null) => void;
  startDate: string | null;
  endDate: string | null;
  empEvalHistory: { user_id: number; name: string; records: { emp_eval_id: number; evaluation_date: string | null; target_date: string | null; category: string; evaluation_type: string; comment: string | null; score: number }[] } | undefined;
  loadingHistory: boolean;
  monthlyTrend: { month: string; count: number }[];
  queryClient: ReturnType<typeof useQueryClient>;
}

function DetailsTab({
  empEvalRankings, selectedEmployee, setSelectedEmployee,
  startDate, endDate, empEvalHistory, loadingHistory, monthlyTrend, queryClient,
}: DetailsTabProps) {
  const today = new Date().toISOString().slice(0, 10);
  const [subTab, setSubTab] = useState<"history" | "feedback">("history");
  const [showForm, setShowForm] = useState(false);
  const [targetDate, setTargetDate] = useState(today);
  const [category, setCategory] = useState("신체");
  const [evalType, setEvalType] = useState("누락");
  const [comment, setComment] = useState("");
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  // 인라인 수정 상태
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editData, setEditData] = useState({ targetDate: "", category: "", evalType: "", comment: "" });
  const [updating, setUpdating] = useState(false);

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ["dashboard-emp-eval-history"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard-emp-eval-rankings"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard-employee-monthly-trend"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard-kpi-summary"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard-period-comparison"] });
  };

  const handleCreate = async () => {
    if (!selectedEmployee) return;
    setSaving(true);
    try {
      await employeeEvaluationsApi.create({
        record_id: null,
        target_user_id: selectedEmployee.user_id,
        category,
        evaluation_type: evalType,
        evaluation_date: today,
        target_date: targetDate || null,
        evaluator_user_id: null,
        score: 1,
        comment: comment.trim() || null,
      });
      toast.success("평가가 저장되었습니다.");
      setComment("");
      setTargetDate(today);
      setShowForm(false);
      invalidateAll();
    } catch {
      toast.error("평가 저장 실패");
    } finally {
      setSaving(false);
    }
  };

  const handleStartEdit = (r: { emp_eval_id: number; target_date: string | null; category: string; evaluation_type: string; comment: string | null }) => {
    setEditingId(r.emp_eval_id);
    setEditData({
      targetDate: r.target_date ?? "",
      category: r.category,
      evalType: r.evaluation_type,
      comment: r.comment ?? "",
    });
  };

  const handleUpdate = async () => {
    if (!editingId) return;
    setUpdating(true);
    try {
      await employeeEvaluationsApi.update(editingId, {
        evaluation_date: today,
        target_date: editData.targetDate || null,
        category: editData.category,
        evaluation_type: editData.evalType,
        comment: editData.comment.trim() || null,
        score: 1,
      });
      toast.success("수정되었습니다.");
      setEditingId(null);
      invalidateAll();
    } catch {
      toast.error("수정 실패");
    } finally {
      setUpdating(false);
    }
  };

  const handleDelete = async (evalId: number) => {
    setDeletingId(evalId);
    try {
      await employeeEvaluationsApi.delete(evalId);
      toast.success("평가가 삭제되었습니다.");
      invalidateAll();
    } catch {
      toast.error("삭제 실패");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div>
      {/* 직원 선택 */}
      <div className="mb-4">
        <select
          value={selectedEmployee?.user_id ?? ""}
          onChange={(e) => {
            const emp = empEvalRankings.find(
              (r) => r.user_id === parseInt(e.target.value)
            );
            setSelectedEmployee(emp ?? null);
            setShowForm(false);
            setEditingId(null);
          }}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
        >
          <option value="">직원 선택</option>
          {empEvalRankings.map((r) => (
            <option key={r.user_id} value={r.user_id}>
              {r.name} ({r.total_count}건)
            </option>
          ))}
        </select>
      </div>

      {/* 서브탭 */}
      <div className="flex gap-1 mb-4 border-b border-gray-200">
        <button
          onClick={() => setSubTab("history")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            subTab === "history"
              ? "border-blue-500 text-blue-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          평가 이력
        </button>
        <button
          onClick={() => setSubTab("feedback")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            subTab === "feedback"
              ? "border-blue-500 text-blue-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          AI 피드백
        </button>
      </div>

      {subTab === "history" && (
        <>
          {!selectedEmployee ? (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
              직원을 선택하세요.
            </div>
          ) : loadingHistory ? (
            <div className="flex justify-center py-8">
              <Loader2 size={24} className="animate-spin text-gray-400" />
            </div>
          ) : empEvalHistory ? (
            <div className="space-y-4">
              {/* 프로필 요약 KPI */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
                  <p className="text-xs text-gray-500 mb-1">총 지적 횟수</p>
                  <p className="text-2xl font-bold text-gray-800">{empEvalHistory.records.length}건</p>
                </div>
                <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
                  <p className="text-xs text-gray-500 mb-1">주요 지적 유형</p>
                  <p className="text-lg font-bold text-gray-800">
                    {(() => {
                      const counts: Record<string, number> = {};
                      empEvalHistory.records.forEach((r) => {
                        counts[r.evaluation_type] = (counts[r.evaluation_type] ?? 0) + 1;
                      });
                      const top = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
                      return top ? top[0] : "-";
                    })()}
                  </p>
                </div>
                <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
                  <p className="text-xs text-gray-500 mb-1">취약 카테고리</p>
                  <p className="text-lg font-bold text-gray-800">
                    {(() => {
                      const counts: Record<string, number> = {};
                      empEvalHistory.records.forEach((r) => {
                        counts[r.category] = (counts[r.category] ?? 0) + 1;
                      });
                      const top = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
                      return top ? top[0] : "-";
                    })()}
                  </p>
                </div>
              </div>

              {/* 월별 지적 건수 추이 미니차트 */}
              {monthlyTrend.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 p-5">
                  <h3 className="font-semibold text-gray-700 mb-3">월별 지적 건수 추이</h3>
                  <ResponsiveContainer width="100%" height={160}>
                    <BarChart data={monthlyTrend}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                      <Tooltip />
                      <Bar dataKey="count" name="건수" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* 평가 추가 폼 */}
              {!showForm ? (
                <button
                  onClick={() => { setShowForm(true); setTargetDate(today); }}
                  className="flex items-center gap-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-xs hover:bg-blue-700"
                >
                  <Plus size={14} /> 평가 추가
                </button>
              ) : (
                <div className="bg-white rounded-xl border border-blue-200 p-4">
                  <h3 className="text-sm font-semibold text-gray-700 mb-3">
                    {empEvalHistory.name} — 평가 추가
                  </h3>
                  <div className="grid grid-cols-4 gap-3">
                    <div>
                      <label className="text-xs text-gray-500 mb-1 block">해당 날짜</label>
                      <input
                        type="date"
                        value={targetDate}
                        onChange={(e) => setTargetDate(e.target.value)}
                        className="w-full text-xs border border-gray-200 rounded px-2 py-1.5"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-gray-500 mb-1 block">카테고리</label>
                      <select value={category} onChange={(e) => setCategory(e.target.value)}
                        className="w-full text-xs border border-gray-200 rounded px-2 py-1.5">
                        {CATEGORY_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="text-xs text-gray-500 mb-1 block">평가 유형</label>
                      <select value={evalType} onChange={(e) => setEvalType(e.target.value)}
                        className="w-full text-xs border border-gray-200 rounded px-2 py-1.5">
                        {EVAL_TYPE_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="text-xs text-gray-500 mb-1 block">코멘트 (선택)</label>
                      <input
                        type="text"
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                        placeholder="코멘트 입력"
                        className="w-full text-xs border border-gray-200 rounded px-2 py-1.5"
                      />
                    </div>
                  </div>
                  <div className="flex gap-2 mt-3">
                    <button onClick={handleCreate} disabled={saving}
                      className="flex items-center gap-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-xs hover:bg-blue-700 disabled:opacity-50">
                      {saving && <Loader2 size={12} className="animate-spin" />} 저장
                    </button>
                    <button onClick={() => setShowForm(false)}
                      className="px-4 py-2 border border-gray-200 text-gray-600 rounded-lg text-xs hover:bg-gray-50">
                      취소
                    </button>
                  </div>
                </div>
              )}

              {/* 평가 이력 테이블 */}
              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-100">
                  <h3 className="font-semibold text-gray-700">
                    {empEvalHistory.name} — 평가 이력
                  </h3>
                </div>
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      {["평가일자", "해당날짜", "카테고리", "평가유형", "코멘트", "관리"].map((h, i) => (
                        <th
                          key={i}
                          className="px-4 py-3 text-left text-xs font-medium text-gray-500"
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {empEvalHistory.records.map((r) =>
                      editingId === r.emp_eval_id ? (
                        <tr key={r.emp_eval_id} className="bg-yellow-50">
                          <td colSpan={6} className="px-4 py-3">
                            <div className="grid grid-cols-5 gap-2 items-end">
                              <div>
                                <label className="text-xs text-gray-500 block mb-1">해당 날짜</label>
                                <input type="date" value={editData.targetDate}
                                  onChange={(e) => setEditData({ ...editData, targetDate: e.target.value })}
                                  className="w-full text-xs border border-gray-200 rounded px-2 py-1.5" />
                              </div>
                              <div>
                                <label className="text-xs text-gray-500 block mb-1">카테고리</label>
                                <select value={editData.category}
                                  onChange={(e) => setEditData({ ...editData, category: e.target.value })}
                                  className="w-full text-xs border border-gray-200 rounded px-2 py-1.5">
                                  {CATEGORY_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
                                </select>
                              </div>
                              <div>
                                <label className="text-xs text-gray-500 block mb-1">평가 유형</label>
                                <select value={editData.evalType}
                                  onChange={(e) => setEditData({ ...editData, evalType: e.target.value })}
                                  className="w-full text-xs border border-gray-200 rounded px-2 py-1.5">
                                  {EVAL_TYPE_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
                                </select>
                              </div>
                              <div>
                                <label className="text-xs text-gray-500 block mb-1">코멘트</label>
                                <input type="text" value={editData.comment}
                                  onChange={(e) => setEditData({ ...editData, comment: e.target.value })}
                                  className="w-full text-xs border border-gray-200 rounded px-2 py-1.5" />
                              </div>
                              <div className="flex gap-1">
                                <button onClick={handleUpdate} disabled={updating}
                                  className="p-1.5 text-green-600 hover:bg-green-50 rounded disabled:opacity-50" title="저장">
                                  {updating ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                                </button>
                                <button onClick={() => setEditingId(null)}
                                  className="p-1.5 text-gray-400 hover:bg-gray-100 rounded" title="취소">
                                  <X size={14} />
                                </button>
                              </div>
                            </div>
                          </td>
                        </tr>
                      ) : (
                        <tr key={r.emp_eval_id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-gray-600 text-xs">{r.evaluation_date ?? "-"}</td>
                          <td className="px-4 py-3 text-gray-600 text-xs">{r.target_date ?? "-"}</td>
                          <td className="px-4 py-3">
                            <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">
                              {r.category}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className="text-xs px-2 py-0.5 rounded-full font-medium text-white"
                              style={{ backgroundColor: EVAL_TYPE_COLORS[r.evaluation_type] ?? "#94a3b8" }}
                            >
                              {r.evaluation_type}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-gray-500 text-xs max-w-[200px] truncate" title={r.comment ?? ""}>
                            {r.comment ?? "-"}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex gap-1 justify-end">
                              <button
                                onClick={() => handleStartEdit(r)}
                                className="text-gray-400 hover:text-blue-500"
                                title="수정"
                              >
                                <Pencil size={14} />
                              </button>
                              <button
                                onClick={() => handleDelete(r.emp_eval_id)}
                                disabled={deletingId === r.emp_eval_id}
                                className="text-gray-400 hover:text-red-500 disabled:opacity-50"
                                title="삭제"
                              >
                                {deletingId === r.emp_eval_id ? (
                                  <Loader2 size={14} className="animate-spin" />
                                ) : (
                                  <Trash2 size={14} />
                                )}
                              </button>
                            </div>
                          </td>
                        </tr>
                      )
                    )}
                    {empEvalHistory.records.length === 0 && (
                      <tr>
                        <td colSpan={6} className="text-center py-6 text-gray-400">
                          해당 기간 평가 이력 없음
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}
        </>
      )}
      {subTab === "feedback" && selectedEmployee && (
        <AiFeedbackPanel userId={selectedEmployee.user_id} />
      )}
      {subTab === "feedback" && !selectedEmployee && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
          직원을 선택하세요.
        </div>
      )}
    </div>
  );
}

// ── KPI 카드 ──────────────────────────────────────────────────
interface KpiCardProps {
  icon: React.ReactNode;
  label: string;
  value: number | string;
  color: "blue" | "purple" | "green" | "yellow";
  delta?: number | null;
  invertColor?: boolean;
  subtitle?: string;
}

const colorMap = {
  blue: "text-blue-600 bg-blue-50",
  purple: "text-purple-600 bg-purple-50",
  green: "text-green-600 bg-green-50",
  yellow: "text-yellow-600 bg-yellow-50",
};

function KpiCard({ icon, label, value, color, delta, invertColor, subtitle }: KpiCardProps) {
  const deltaColor =
    delta == null
      ? ""
      : invertColor
        ? delta > 0
          ? "text-red-500"
          : "text-green-500"
        : delta > 0
          ? "text-green-500"
          : "text-red-500";

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-center gap-3 mb-3">
        <div className={cn("p-2 rounded-lg", colorMap[color])}>{icon}</div>
        <span className="text-sm text-gray-500">{label}</span>
      </div>
      <div className="flex items-end gap-2">
        <p className="text-2xl font-bold text-gray-800">{value}</p>
        {delta != null && (
          <span className={cn("text-xs font-semibold mb-1", deltaColor)}>
            {delta > 0 ? "+" : ""}{delta}%
            {invertColor ? (delta > 0 ? " ↑" : " ↓") : (delta > 0 ? " ↑" : " ↓")}
          </span>
        )}
      </div>
      {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
    </div>
  );
}
