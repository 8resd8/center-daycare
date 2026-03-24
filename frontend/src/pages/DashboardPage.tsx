import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
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
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
} from "recharts";
import { Loader2, TrendingUp, Users, FileText, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { useFilterStore } from "@/store/filterStore";
import { dashboardApi } from "@/api/dashboard";
import type { EmpEvalRankingItem } from "@/types";

type DashTab = "stats" | "rankings" | "details";

// 평가 유형 색상
const EVAL_TYPE_COLORS: Record<string, string> = {
  누락: "#dc2626",
  내용부족: "#f97316",
  오타: "#eab308",
  문법: "#10b981",
  오류: "#8b5cf6",
};

// AI 등급 색상
const GRADE_COLORS: Record<string, string> = {
  우수: "#22c55e",
  평균: "#eab308",
  개선: "#ef4444",
};

export default function DashboardPage() {
  const { startDate, endDate, setThisMonth, setLastMonth, setDateRange } =
    useFilterStore();
  const [activeTab, setActiveTab] = useState<DashTab>("stats");
  const [selectedEmployee, setSelectedEmployee] =
    useState<EmpEvalRankingItem | null>(null);

  const { data: summary, isLoading: loadingSummary } = useQuery({
    queryKey: ["dashboard-summary", startDate, endDate],
    queryFn: () =>
      dashboardApi.summary(startDate ?? undefined, endDate ?? undefined),
  });

  // 직원 평가 추이 (항상 데이터 있음)
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

  // AI 등급 분포
  const { data: gradeDist = [] } = useQuery({
    queryKey: ["dashboard-grade-dist", startDate, endDate],
    queryFn: () =>
      dashboardApi.gradeDist(startDate ?? undefined, endDate ?? undefined),
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

  // 집중관리 필요 직원 (5건 이상)
  const highRiskCount = empEvalRankings.filter((e) => e.total_count >= 5).length;
  const totalIssues = empEvalRankings.reduce((s, e) => s + e.total_count, 0);
  const topType = (() => {
    if (empEvalTrend.length === 0) return null;
    const totals: Record<string, number> = { 누락: 0, 내용부족: 0, 오타: 0, 문법: 0, 오류: 0 };
    for (const row of empEvalTrend) {
      totals["누락"] += row["누락"];
      totals["내용부족"] += row["내용부족"];
      totals["오타"] += row["오타"];
      totals["문법"] += row["문법"];
      totals["오류"] += row["오류"];
    }
    const max = Object.entries(totals).sort((a, b) => b[1] - a[1])[0];
    return max && max[1] > 0 ? max[0] : null;
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
        {loadingSummary ? (
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
              value={`${totalIssues}건`}
              color="blue"
            />
            <KpiCard
              icon={<TrendingUp size={20} />}
              label="가장 많은 지적 유형"
              value={topType ?? "-"}
              color="purple"
            />
            <KpiCard
              icon={<AlertTriangle size={20} />}
              label="집중 관리 필요 (5건↑)"
              value={`${highRiskCount}명`}
              color="yellow"
            />
            <KpiCard
              icon={<Users size={20} />}
              label="재직 직원"
              value={`${summary?.total_employees ?? 0}명`}
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

          {/* 카테고리 분포 + AI 등급 분포 (2열) */}
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

            {/* AI 평가 등급 분포 원형 차트 */}
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-700 mb-4">AI 평가 등급 분포</h3>
              {gradeDist.length === 0 ? (
                <div className="text-center py-8 text-gray-400 text-sm">
                  AI 평가 데이터 없음
                </div>
              ) : (
                <div className="flex items-center gap-6">
                  <ResponsiveContainer width={180} height={180}>
                    <PieChart>
                      <Pie
                        data={gradeDist}
                        dataKey="count"
                        nameKey="grade"
                        cx="50%"
                        cy="50%"
                        innerRadius={40}
                        outerRadius={75}
                        label={({ grade, percent }) =>
                          `${grade} ${((percent ?? 0) * 100).toFixed(0)}%`
                        }
                        labelLine={false}
                      >
                        {gradeDist.map((entry, i) => (
                          <Cell
                            key={i}
                            fill={GRADE_COLORS[entry.grade] ?? "#94a3b8"}
                          />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="space-y-2 flex-1">
                    {gradeDist.map((item) => (
                      <div key={item.grade} className="flex items-center gap-2">
                        <div
                          className="w-3 h-3 rounded-full flex-shrink-0"
                          style={{ backgroundColor: GRADE_COLORS[item.grade] ?? "#94a3b8" }}
                        />
                        <span className="text-sm text-gray-600">
                          {item.grade}: {item.count}건
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
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
                      {["평가일자", "해당날짜", "카테고리", "평가유형", "코멘트"].map((h) => (
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
                    {empEvalHistory.records.map((r) => (
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
                        <td className="px-4 py-3 text-gray-500 text-xs max-w-[250px] truncate" title={r.comment ?? ""}>
                          {r.comment ?? "-"}
                        </td>
                      </tr>
                    ))}
                    {empEvalHistory.records.length === 0 && (
                      <tr>
                        <td colSpan={5} className="text-center py-6 text-gray-400">
                          해당 기간 평가 이력 없음
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}
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
}

const colorMap = {
  blue: "text-blue-600 bg-blue-50",
  purple: "text-purple-600 bg-purple-50",
  green: "text-green-600 bg-green-50",
  yellow: "text-yellow-600 bg-yellow-50",
};

function KpiCard({ icon, label, value, color }: KpiCardProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-center gap-3 mb-3">
        <div className={cn("p-2 rounded-lg", colorMap[color])}>{icon}</div>
        <span className="text-sm text-gray-500">{label}</span>
      </div>
      <p className="text-2xl font-bold text-gray-800">{value}</p>
    </div>
  );
}
