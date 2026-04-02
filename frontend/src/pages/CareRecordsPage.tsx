import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2, Copy, Check, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { useFilterStore } from "@/store/filterStore";
import { dailyRecordsApi } from "@/api/dailyRecords";
import { weeklyReportsApi } from "@/api/weeklyReports";
import { employeeEvaluationsApi } from "@/api/employeeEvaluations";
import type { DailyRecord, WeeklyTableRow, ProgEntry } from "@/types";
import { checkRecord, calcRate } from "@/lib/careRecordCheck";
import type { CheckResult, CheckCategory } from "@/lib/careRecordCheck";
import BulkEvalModal from "@/components/BulkEvalModal";

type MainTab = "weekly" | "daily";
type WeeklySubTab = "basic" | "physical" | "cognitive" | "nursing" | "recovery";

const WEEKLY_SUB_TABS: { key: WeeklySubTab; label: string }[] = [
  { key: "basic", label: "기본정보" },
  { key: "physical", label: "신체활동지원" },
  { key: "cognitive", label: "인지관리" },
  { key: "nursing", label: "간호관리" },
  { key: "recovery", label: "기능회복훈련" },
];

const COGNITIVE_FIELDS: { label: string; key: keyof DailyRecord }[] = [
  { label: "날짜", key: "date" }, { label: "특이사항", key: "cognitive_note" },
  { label: "인지관리지원", key: "cog_support" }, { label: "의사소통도움", key: "comm_support" },
  { label: "작성자", key: "writer_cog" },
];
const NURSING_FIELDS: { label: string; key: keyof DailyRecord }[] = [
  { label: "날짜", key: "date" }, { label: "특이사항", key: "nursing_note" },
  { label: "혈압/체온", key: "bp_temp" }, { label: "건강관리(5분)", key: "health_manage" },
  { label: "간호관리", key: "nursing_manage" }, { label: "응급서비스", key: "emergency" },
  { label: "작성자", key: "writer_nur" },
];
const RECOVERY_FIELDS: { label: string; key: keyof DailyRecord }[] = [
  { label: "날짜", key: "date" }, { label: "특이사항", key: "functional_note" },
  { label: "향상 프로그램 내용", key: "prog_enhance_detail" },
  { label: "향상 프로그램 여부", key: "prog_basic" }, { label: "인지활동 프로그램", key: "prog_activity" },
  { label: "인지기능 훈련", key: "prog_cognitive" }, { label: "물리치료", key: "prog_therapy" },
  { label: "작성자", key: "writer_func" },
];

// ── 메인 컴포넌트 ──────────────────────────────────────────────
export default function CareRecordsPage() {
  const { startDate, endDate, selectedCustomerId } = useFilterStore();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<MainTab>("weekly");
  const [weeklySubTab, setWeeklySubTab] = useState<WeeklySubTab>("basic");
  const [generatedReport, setGeneratedReport] = useState("");
  const [copied, setCopied] = useState(false);
  const [bulkWeeklyGenerating, setBulkWeeklyGenerating] = useState(false);
  const [bulkWeeklyProgress, setBulkWeeklyProgress] = useState<{ current: number; total: number; name: string } | null>(null);
  const [showBulkModal, setShowBulkModal] = useState(false);

  const { data: customersWithRecords = [] } = useQuery({
    queryKey: ["customers-with-records", startDate, endDate],
    queryFn: () => dailyRecordsApi.customersWithRecords({ start_date: startDate ?? undefined, end_date: endDate ?? undefined }),
  });

  const { data: records = [], isLoading: loadingRecords } = useQuery({
    queryKey: ["daily-records", selectedCustomerId, startDate, endDate],
    queryFn: () => dailyRecordsApi.list({ customer_id: selectedCustomerId!, start_date: startDate ?? undefined, end_date: endDate ?? undefined }),
    enabled: !!selectedCustomerId,
  });

  // 전주/이번주 변화량 분석 자동 조회
  const analysisQueryKey = ["weekly-analysis", selectedCustomerId, startDate, endDate];
  const { data: analysisData, isLoading: loadingAnalysis } = useQuery({
    queryKey: analysisQueryKey,
    queryFn: () => weeklyReportsApi.analysis({ customer_id: selectedCustomerId!, start_date: startDate!, end_date: endDate! }),
    enabled: !!selectedCustomerId && !!startDate && !!endDate,
  });

  // 기존 저장된 주간 보고서 자동 조회
  const weeklyReportQueryKey = ["weekly-report", selectedCustomerId, startDate, endDate];
  const { data: existingReports = [], isLoading: loadingReport } = useQuery({
    queryKey: weeklyReportQueryKey,
    queryFn: () => weeklyReportsApi.list({ customer_id: selectedCustomerId!, start_date: startDate ?? undefined, end_date: endDate ?? undefined }),
    enabled: !!selectedCustomerId && !!startDate && !!endDate,
  });
  const existingReportText = existingReports[0]?.report_text ?? null;

  const { data: users = [] } = useQuery({
    queryKey: ["employee-eval-users"],
    queryFn: employeeEvaluationsApi.users,
  });

  // 기존 보고서 로드 시 textarea에 반영
  useEffect(() => {
    setGeneratedReport(existingReportText ?? "");
  }, [existingReportText]);

  const generateMutation = useMutation({
    mutationFn: () => weeklyReportsApi.generate({ customer_id: selectedCustomerId!, start_date: startDate!, end_date: endDate! }),
    onSuccess: async (data) => {
      setGeneratedReport(data.report_text);
      try {
        await weeklyReportsApi.save(selectedCustomerId!, { customer_id: selectedCustomerId!, start_date: startDate!, end_date: endDate!, report_text: data.report_text });
        queryClient.invalidateQueries({ queryKey: weeklyReportQueryKey });
        toast.success("기록지가 저장되었습니다.");
      } catch {
        toast.error("생성은 완료됐으나 저장에 실패했습니다.");
      }
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "생성 실패";
      toast.error(msg);
    },
  });

  const handleCopy = async () => {
    await navigator.clipboard.writeText(generatedReport);
    setCopied(true);
    toast.success("클립보드에 복사됨");
    setTimeout(() => setCopied(false), 2000);
  };

  const handleBulkWeekly = async () => {
    if (!startDate || !endDate || customersWithRecords.length === 0) {
      toast.info("날짜 범위와 수급자 목록이 필요합니다.");
      return;
    }
    setBulkWeeklyGenerating(true);
    const total = customersWithRecords.length;
    let success = 0, fail = 0;

    for (let i = 0; i < total; i++) {
      const customer = customersWithRecords[i];
      setBulkWeeklyProgress({ current: i + 1, total, name: customer.name });
      try {
        const result = await weeklyReportsApi.generate({
          customer_id: customer.customer_id,
          start_date: startDate,
          end_date: endDate,
        });
        await weeklyReportsApi.save(customer.customer_id, {
          customer_id: customer.customer_id,
          start_date: startDate,
          end_date: endDate,
          report_text: result.report_text,
        });
        success++;
      } catch {
        fail++;
      }
    }

    setBulkWeeklyGenerating(false);
    setBulkWeeklyProgress(null);
    toast.success(`일괄 생성 완료: ${success}건 성공${fail ? `, ${fail}건 실패` : ""}`);
  };

  const selectedCustomer = customersWithRecords.find((c) => c.customer_id === selectedCustomerId);
  const checkResults = records.map(checkRecord);

  // PDF 기록에서 작성자 목록 추출
  const writerNames = [...new Set(
    records.flatMap((r) => [r.writer_phy, r.writer_cog, r.writer_nur, r.writer_func].filter((w): w is string => !!w?.trim()))
  )].sort();

  if (!selectedCustomerId) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        <p>왼쪽 사이드바에서 수급자를 선택하세요.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <BulkEvalModal
        open={showBulkModal}
        onClose={() => setShowBulkModal(false)}
        records={records}
        users={users}
      />
      {/* 수급자 정보 헤더 */}
      {selectedCustomer && (
        <div className="bg-white rounded-xl border border-gray-200 px-4 py-3">
          <div className="flex items-baseline gap-3">
            <h2 className="text-base font-bold text-gray-800 whitespace-nowrap">{selectedCustomer.name} 어르신</h2>
            <span className="text-xs text-gray-400 whitespace-nowrap">
              {[
                selectedCustomer.birth_date,
                `기록 ${selectedCustomer.record_count}건`,
              ].filter(Boolean).join("  ·  ")}
            </span>
          </div>
        </div>
      )}

      {/* 메인 탭 */}
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

      {loadingRecords ? (
        <div className="flex justify-center py-12"><Loader2 size={24} className="animate-spin text-gray-400" /></div>
      ) : (
        <>
          {/* ── 주간상태변화 평가 ── */}
          {activeTab === "weekly" && (
            <div className="space-y-4">
              {/* 전체인원 일괄 생성 */}
              <div className="bg-white rounded-xl border border-gray-200 p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700">전체인원 주간상태변화 기록지 일괄 생성</h3>
                    <p className="text-xs text-gray-400 mt-0.5">
                      현재 날짜 범위의 수급자 {customersWithRecords.length}명 보고서를 순서대로 생성·저장합니다.
                    </p>
                  </div>
                  <button
                    onClick={handleBulkWeekly}
                    disabled={bulkWeeklyGenerating || !startDate || !endDate || customersWithRecords.length === 0}
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50 whitespace-nowrap"
                  >
                    {bulkWeeklyGenerating && <Loader2 size={14} className="animate-spin" />}
                    전체 인원 기록지 생성
                  </button>
                </div>
                {bulkWeeklyProgress && (
                  <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                    <p className="text-xs text-gray-600">
                      {bulkWeeklyProgress.name} 처리 중... ({bulkWeeklyProgress.current}/{bulkWeeklyProgress.total})
                    </p>
                    <div className="mt-1.5 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-green-500 rounded-full transition-all duration-300"
                        style={{ width: `${(bulkWeeklyProgress.current / bulkWeeklyProgress.total) * 100}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* 5개 서브탭 데이터 */}
              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <div className="flex border-b border-gray-200">
                  {WEEKLY_SUB_TABS.map((t) => (
                    <button key={t.key} onClick={() => setWeeklySubTab(t.key)}
                      className={cn("flex-1 py-2 text-xs font-medium transition-colors",
                        weeklySubTab === t.key ? "bg-blue-50 text-blue-700 border-b-2 border-blue-600" : "text-gray-500 hover:bg-gray-50"
                      )}>
                      {t.label}
                    </button>
                  ))}
                </div>
                <div className="overflow-x-auto p-2">
                  {records.length === 0
                    ? <p className="text-center text-gray-400 text-sm py-8">해당 기간 기록이 없습니다.</p>
                    : <DataTable records={records} subTab={weeklySubTab} />
                  }
                </div>
              </div>

              {/* 지난주/이번주 변화량 */}
              {(loadingAnalysis || analysisData) && (
                <WeeklyChangePanel
                  weeklyTable={analysisData?.weekly_table ?? []}
                  prevRange={analysisData?.prev_range ?? null}
                  currRange={analysisData?.curr_range ?? null}
                  loading={loadingAnalysis}
                  prevProgEntries={analysisData?.prev_prog_entries ?? []}
                  currProgEntries={analysisData?.curr_prog_entries ?? []}
                />
              )}

              {/* AI 주간 보고서 생성 (선택된 수급자) */}
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-gray-700">
                      {selectedCustomer ? `${selectedCustomer.name} 주간상태변화 기록지` : "주간상태변화 기록지"}
                    </h3>
                    {existingReportText && (
                      <span className="text-xs bg-green-50 text-green-600 px-2 py-0.5 rounded-full">저장됨</span>
                    )}
                  </div>
                  <button
                    onClick={() => generateMutation.mutate()}
                    disabled={generateMutation.isPending || !startDate || !endDate}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
                  >
                    {generateMutation.isPending && <Loader2 size={14} className="animate-spin" />}
                    {existingReportText ? "재생성" : "생성하기"}
                  </button>
                </div>
                {loadingReport ? (
                  <div className="flex justify-center py-8">
                    <Loader2 size={20} className="animate-spin text-gray-400" />
                  </div>
                ) : generatedReport ? (
                  <div>
                    <div className="flex items-center justify-end mb-2">
                      <button onClick={handleCopy} className="flex items-center gap-1 text-xs px-3 py-1 border border-gray-200 rounded-lg hover:bg-gray-50">
                        {copied ? <Check size={12} className="text-green-600" /> : <Copy size={12} />} 복사
                      </button>
                    </div>
                    <textarea value={generatedReport} onChange={(e) => setGeneratedReport(e.target.value)}
                      className="w-full h-72 text-sm border border-gray-200 rounded-lg p-3 resize-none focus:outline-none focus:ring-2 focus:ring-blue-300" />
                  </div>
                ) : (
                  <p className="text-center text-gray-400 text-sm py-8">
                    {!startDate || !endDate ? "날짜 범위를 먼저 설정하세요." : "생성하기 버튼을 눌러 주간 보고서를 생성하세요."}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* ── 일일 특이사항 평가 ── */}
          {activeTab === "daily" && (
            <div className="space-y-4">
              {records.length === 0 ? (
                <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">해당 기간 기록이 없습니다.</div>
              ) : (
                <>
                  {/* 카테고리별 작성률 */}
                  <div className="bg-white rounded-xl border border-gray-200 p-4">
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">카테고리별 작성률</h3>
                    <div className="grid grid-cols-5 gap-3">
                      {(["basic","physical","cognitive","nursing","recovery"] as CheckCategory[]).map((cat) => {
                        const labels: Record<CheckCategory, string> = { basic:"기본정보", physical:"신체활동", cognitive:"인지관리", nursing:"간호관리", recovery:"기능회복" };
                        const rate = calcRate(checkResults, cat);
                        return (
                          <div key={cat} className="text-center">
                            <p className="text-xs text-gray-500 mb-1">{labels[cat]}</p>
                            <p className={cn("text-xl font-bold", rate < 100 ? "text-orange-500" : "text-gray-800")}>{rate}%</p>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* 필수항목 체크 테이블 */}
                  <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                    <div className="p-3 border-b border-gray-100">
                      <h3 className="text-sm font-semibold text-gray-700">필수 항목 체크</h3>
                    </div>
                    <CheckTable checkResults={checkResults} />
                  </div>

                  {/* 추가 정보 */}
                  <AdditionalInfoSection records={records} />

                  {/* 직원 평가 */}
                  {writerNames.length > 0 && records.length > 0 && (
                    <EmployeeEvalForm records={records} writerNames={writerNames} />
                  )}
                </>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── 지난주/이번주 변화량 패널 ──────────────────────────────────────
function WeeklyChangePanel({
  weeklyTable,
  prevRange,
  currRange,
  loading,
  prevProgEntries,
  currProgEntries,
}: {
  weeklyTable: WeeklyTableRow[];
  prevRange: [string, string] | null;
  currRange: [string, string] | null;
  loading?: boolean;
  prevProgEntries: ProgEntry[];
  currProgEntries: ProgEntry[];
}) {
  const TABLE_COLS: { key: keyof WeeklyTableRow; label: string }[] = [
    { key: "주간", label: "주간" },
    { key: "출석일", label: "출석일" },
    { key: "식사량(일반식)", label: "일반식" },
    { key: "식사량(죽식)", label: "죽식" },
    { key: "식사량(다진식)", label: "다진식" },
    { key: "소변", label: "소변" },
    { key: "대변", label: "대변" },
    { key: "기저귀교환", label: "기저귀교환" },
  ];

  // MM-DD 형식
  const fmt = (d: string) => d.slice(5);

  const rangeLabel = (rowIdx: number) => {
    const range = rowIdx === 0 ? prevRange : currRange;
    if (!range) return null;
    return `${fmt(range[0])} ~ ${fmt(range[1])}`;
  };

  const [progTab, setProgTab] = useState<"curr" | "prev">("curr");
  const progEntries = progTab === "curr" ? currProgEntries : prevProgEntries;
  const hasAnyProg = prevProgEntries.length > 0 || currProgEntries.length > 0;

  const parseNum = (v: string | number | undefined): number | null => {
    if (v === undefined || v === null || (v as string) === "-") return null;
    const n = parseFloat(String(v).replace("회", ""));
    return isNaN(n) ? null : n;
  };
  const prevRow = weeklyTable.length >= 2 ? weeklyTable[0] : null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-100 flex items-center gap-2">
        <h3 className="text-sm font-semibold text-gray-700">지난주 / 이번주 변화량</h3>
        {loading && <Loader2 size={13} className="animate-spin text-gray-400" />}
      </div>

      {loading ? (
        <div className="flex justify-center py-8">
          <Loader2 size={20} className="animate-spin text-gray-300" />
        </div>
      ) : (
        <>
          {/* 출석/식사/배설 비교 테이블 */}
          {weeklyTable.length > 0 && (
            <div className="overflow-x-auto px-4 pt-3">
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="bg-gray-50">
                    {/* 주간 컬럼: 내용 길이에 맞춤 */}
                    <th className="border border-gray-200 px-2 py-1.5 text-left whitespace-nowrap w-px font-medium text-gray-600">주간</th>
                    {TABLE_COLS.slice(1).map((c) => (
                      <th key={c.key} className="border border-gray-200 px-2 py-1.5 text-center whitespace-nowrap font-medium text-gray-600">
                        {c.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {weeklyTable.map((row, i) => (
                    <tr key={i} className={cn("text-center", row.주간 === "이번주" ? "bg-blue-50" : "")}>
                      <td className="border border-gray-200 px-2 py-1.5 whitespace-nowrap w-px text-left font-semibold">
                        {row.주간}
                        {rangeLabel(i) && (
                          <span className="ml-1 font-normal text-gray-400 text-[11px]">({rangeLabel(i)})</span>
                        )}
                      </td>
                      {TABLE_COLS.slice(1).map((c) => {
                        let colorClass = "";
                        if (row.주간 === "이번주" && prevRow) {
                          const prev = parseNum(prevRow[c.key]);
                          const curr = parseNum(row[c.key]);
                          if (prev !== null && curr !== null) {
                            if (curr < prev) colorClass = "text-blue-600 font-semibold";
                            else if (curr > prev) colorClass = "text-red-600 font-semibold";
                          }
                        }
                        return (
                          <td key={c.key} className={cn("border border-gray-200 px-2 py-1.5 whitespace-nowrap", colorClass)}>
                            {String(row[c.key] ?? "-")}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* 카테고리별 점수 변화 */}
          {hasAnyProg && (
            <div className="px-4 pb-3">
              <div className="rounded-lg border border-gray-200 overflow-hidden">
                {/* 탭 헤더 */}
                <div className="flex border-b border-gray-200">
                  {([
                    { key: "curr" as const, label: "이번주 프로그램", count: currProgEntries.length },
                    { key: "prev" as const, label: "지난주 프로그램", count: prevProgEntries.length },
                  ]).map((t) => (
                    <button
                      key={t.key}
                      onClick={() => setProgTab(t.key)}
                      className={cn(
                        "flex-1 py-1.5 text-xs font-medium transition-colors flex items-center justify-center gap-1",
                        progTab === t.key
                          ? "bg-blue-50 text-blue-700 border-b-2 border-blue-600"
                          : "text-gray-500 hover:bg-gray-50"
                      )}
                    >
                      {t.label}
                      <span className={cn(
                        "px-1.5 py-0.5 rounded-full text-[10px]",
                        progTab === t.key ? "bg-blue-100 text-blue-600" : "bg-gray-100 text-gray-500"
                      )}>
                        {t.count}
                      </span>
                    </button>
                  ))}
                </div>
                {/* 탭 내용 */}
                <div className="p-2.5">
                  {progEntries.length > 0 ? (
                    <div className="space-y-1">
                      {progEntries.map((e, i) => (
                        <div key={i} className="flex gap-2 text-xs">
                          <span className="text-gray-400 whitespace-nowrap shrink-0">{e.date}</span>
                          <span className="text-gray-700 break-all">{e.detail}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-gray-400 text-center py-3">해당 주 프로그램 항목 없음</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {weeklyTable.length === 0 && !hasAnyProg && (
            <p className="text-center text-gray-400 text-xs py-6">해당 기간 분석 데이터가 없습니다.</p>
          )}
        </>
      )}
    </div>
  );
}

// ── 데이터 테이블 ──────────────────────────────────────────────
function DataTable({ records, subTab }: { records: DailyRecord[]; subTab: WeeklySubTab }) {
  if (subTab === "basic") {
    return (
      <table className="w-full text-xs border-collapse">
        <thead><tr className="bg-gray-50">
          {["날짜","총시간","시작시간","종료시간","이동서비스","차량번호"].map((h) => (
            <th key={h} className="border border-gray-200 px-2 py-1 text-left whitespace-nowrap">{h}</th>
          ))}
        </tr></thead>
        <tbody>
          {records.map((r) => (
            <tr key={r.record_id} className="hover:bg-gray-50">
              {([r.date, r.total_service_time, r.start_time, r.end_time, r.transport_service, r.transport_vehicles] as (string | null)[]).map((v, i) => (
                <td key={i} className="border border-gray-200 px-2 py-1 whitespace-nowrap">{v ?? "-"}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    );
  }
  if (subTab === "physical") {
    return (
      <table className="w-full text-xs border-collapse">
        <thead><tr className="bg-gray-50">
          {["날짜","특이사항","세면/구강","목욕","식사","화장실이용하기(기저귀교환)","이동","작성자"].map((h) => (
            <th key={h} className="border border-gray-200 px-2 py-1 text-left whitespace-nowrap">{h}</th>
          ))}
        </tr></thead>
        <tbody>
          {records.map((r) => {
            const meals = [r.meal_breakfast, r.meal_lunch, r.meal_dinner].filter(Boolean).join(" / ");
            const bath = r.bath_time === "없음" ? "없음" : [r.bath_time, r.bath_method].filter(Boolean).join(" / ");
            return (
              <tr key={r.record_id} className="hover:bg-gray-50">
                <td className="border border-gray-200 px-2 py-1 whitespace-nowrap">{r.date}</td>
                <td className="border border-gray-200 px-2 py-1 whitespace-nowrap">{r.physical_note ?? "-"}</td>
                <td className="border border-gray-200 px-2 py-1 whitespace-nowrap">{r.hygiene_care ?? "-"}</td>
                <td className="border border-gray-200 px-2 py-1 whitespace-nowrap">{bath || "-"}</td>
                <td className="border border-gray-200 px-2 py-1 whitespace-nowrap">{meals || "-"}</td>
                <td className="border border-gray-200 px-2 py-1 whitespace-nowrap">{r.toilet_care ?? "-"}</td>
                <td className="border border-gray-200 px-2 py-1 whitespace-nowrap">{r.mobility_care ?? "-"}</td>
                <td className="border border-gray-200 px-2 py-1 whitespace-nowrap">{r.writer_phy ?? "-"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    );
  }
  const fieldMap = { cognitive: COGNITIVE_FIELDS, nursing: NURSING_FIELDS, recovery: RECOVERY_FIELDS };
  const fields = fieldMap[subTab as keyof typeof fieldMap];
  return (
    <table className="w-full text-xs border-collapse">
      <thead><tr className="bg-gray-50">
        {fields.map((f) => <th key={f.key} className="border border-gray-200 px-2 py-1 text-left whitespace-nowrap">{f.label}</th>)}
      </tr></thead>
      <tbody>
        {records.map((r) => (
          <tr key={r.record_id} className="hover:bg-gray-50">
            {fields.map((f) => (
              <td key={f.key} className="border border-gray-200 px-2 py-1 whitespace-nowrap">
                {(r[f.key] as string) ?? "-"}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ── 필수항목 체크 테이블 ─────────────────────────────────────────
function CheckTable({ checkResults }: { checkResults: CheckResult[] }) {
  const [activeCat, setActiveCat] = useState<CheckCategory>("basic");
  const categories: { key: CheckCategory; label: string }[] = [
    { key: "basic", label: "기본정보" }, { key: "physical", label: "신체활동" },
    { key: "cognitive", label: "인지관리" }, { key: "nursing", label: "간호관리" },
    { key: "recovery", label: "기능회복" },
  ];
  const sampleChecks = checkResults[0]?.[activeCat] ?? {};
  const keys = Object.keys(sampleChecks).filter((k) => k !== "writer");
  return (
    <div>
      <div className="flex border-b border-gray-200">
        {categories.map((c) => (
          <button key={c.key} onClick={() => setActiveCat(c.key)}
            className={cn("flex-1 py-2 text-xs font-medium transition-colors",
              activeCat === c.key ? "bg-blue-50 text-blue-700 border-b-2 border-blue-600" : "text-gray-500 hover:bg-gray-50"
            )}>
            {c.label}
          </button>
        ))}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs border-collapse">
          <thead><tr className="bg-gray-50">
            <th className="border border-gray-200 px-2 py-1 text-left whitespace-nowrap">날짜</th>
            <th className="border border-gray-200 px-2 py-1 text-left whitespace-nowrap">작성자</th>
            {keys.map((k) => <th key={k} className="border border-gray-200 px-2 py-1 text-center whitespace-nowrap">{k}</th>)}
          </tr></thead>
          <tbody>
            {checkResults.map((row, i) => {
              const checks = row[activeCat] as Record<string, boolean | null | string>;
              return (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="border border-gray-200 px-2 py-1 whitespace-nowrap">{row.date}</td>
                  <td className="border border-gray-200 px-2 py-1 whitespace-nowrap text-gray-600">{(checks.writer as string) ?? ""}</td>
                  {keys.map((k) => {
                    const v = checks[k];
                    return <td key={k} className="border border-gray-200 px-2 py-1 text-center whitespace-nowrap">
                      {v === null ? <span className="text-gray-300">-</span> : v ? "✅" : "❌"}
                    </td>;
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── 추가 정보 섹션 (접기/펼치기) ──────────────────────────────────
function AdditionalInfoSection({ records }: { records: DailyRecord[] }) {
  const [expanded, setExpanded] = useState(false);

  const counts: { label: string; count: number }[] = [
    { label: "목욕", count: records.filter((r) => r.bath_time?.trim() || r.bath_method?.trim()).length },
    { label: "아침", count: records.filter((r) => r.meal_breakfast?.trim()).length },
    { label: "간호관리", count: records.filter((r) => r.nursing_manage?.trim()).length },
    { label: "응급", count: records.filter((r) => r.emergency?.trim()).length },
    { label: "물리치료", count: records.filter((r) => r.prog_therapy?.trim()).length },
    { label: "향상프로그램", count: records.filter((r) => r.prog_enhance_detail?.trim()).length },
  ].filter((c) => c.count > 0);

  return (
    <div className="bg-white rounded-xl border border-gray-200">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 flex items-center justify-between hover:bg-gray-50 rounded-xl transition-colors"
      >
        <div className="flex items-center gap-2 flex-wrap">
          <h3 className="text-sm font-semibold text-gray-700">추가 정보</h3>
          {counts.length > 0 ? (
            counts.map((c) => (
              <span key={c.label} className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">
                {c.label} {c.count}건
              </span>
            ))
          ) : (
            <span className="text-xs text-gray-400">작성된 내용 없음</span>
          )}
        </div>
        <ChevronDown size={16} className={cn("text-gray-400 transition-transform flex-shrink-0 ml-2", expanded && "rotate-180")} />
      </button>
      {expanded && (
        <div className="overflow-x-auto px-4 pb-4">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50">
                {["날짜", "목욕", "아침", "간호관리", "응급", "물리치료", "향상프로그램내용"].map((h) => (
                  <th key={h} className="border border-gray-200 px-2 py-1 text-left whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr key={r.record_id} className="hover:bg-gray-50">
                  <td className="border border-gray-200 px-2 py-1 whitespace-nowrap">{r.date}</td>
                  <td className="border border-gray-200 px-2 py-1 whitespace-nowrap">
                    {r.bath_time && r.bath_method ? `${r.bath_time} / ${r.bath_method}` : (r.bath_time ?? "-")}
                  </td>
                  <td className="border border-gray-200 px-2 py-1 whitespace-nowrap">{r.meal_breakfast ?? "-"}</td>
                  <td className="border border-gray-200 px-2 py-1 max-w-[120px] truncate">{r.nursing_manage ?? "-"}</td>
                  <td className="border border-gray-200 px-2 py-1 whitespace-nowrap">{r.emergency ?? "-"}</td>
                  <td className="border border-gray-200 px-2 py-1 whitespace-nowrap">{r.prog_therapy ?? "-"}</td>
                  <td className="border border-gray-200 px-2 py-1 max-w-[150px] truncate">{r.prog_enhance_detail ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── 직원 평가 폼 ──────────────────────────────────────────────
const CATEGORY_OPTIONS = ["공통", "신체", "인지", "간호", "기능"];
const EVAL_TYPE_OPTIONS = ["누락", "내용부족", "오타", "문법", "오류"];

function EmployeeEvalForm({ records, writerNames }: { records: DailyRecord[]; writerNames: string[] }) {
  const { data: users = [] } = useQuery({
    queryKey: ["employee-eval-users"],
    queryFn: employeeEvaluationsApi.users,
  });

  const [target, setTarget] = useState(writerNames[0] ?? "");
  const [targetDate, setTargetDate] = useState(records[0]?.date ?? "");
  const [category, setCategory] = useState("신체");
  const [evalType, setEvalType] = useState("누락");
  const [comment, setComment] = useState("");
  const [lastEvalId, setLastEvalId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  const firstRecord = records[0];

  const handleSave = async () => {
    const user = users.find((u) => u.name === target);
    if (!user) { toast.error(`'${target}' 직원을 DB에서 찾을 수 없습니다.`); return; }
    if (!firstRecord) return;
    setSaving(true);
    try {
      const result = await employeeEvaluationsApi.create({
        record_id: firstRecord.record_id,
        target_user_id: user.user_id,
        category,
        evaluation_type: evalType,
        evaluation_date: new Date().toISOString().slice(0, 10),
        target_date: targetDate,
        evaluator_user_id: 1,
        score: 1,
        comment: comment.trim() || null,
      });
      setLastEvalId(result.emp_eval_id);
      setComment("");
      toast.success("평가가 저장되었습니다.");
    } catch { toast.error("평가 저장 실패"); }
    finally { setSaving(false); }
  };

  const handleUndo = async () => {
    if (!lastEvalId) return;
    try {
      await employeeEvaluationsApi.delete(lastEvalId);
      setLastEvalId(null);
      toast.success("저장이 취소되었습니다.");
    } catch { toast.error("되돌리기 실패"); }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">직원 평가 입력</h3>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-2">
          <div>
            <label className="text-xs text-gray-500 mb-1 block">평가 대상</label>
            <select value={target} onChange={(e) => setTarget(e.target.value)}
              className="w-full text-xs border border-gray-200 rounded px-2 py-1.5">
              {writerNames.map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">해당 날짜</label>
            <select value={targetDate} onChange={(e) => setTargetDate(e.target.value)}
              className="w-full text-xs border border-gray-200 rounded px-2 py-1.5">
              {records.map((r) => <option key={r.record_id} value={r.date}>{r.date}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">카테고리</label>
            <select value={category} onChange={(e) => setCategory(e.target.value)}
              className="w-full text-xs border border-gray-200 rounded px-2 py-1.5">
              {CATEGORY_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          </div>
        </div>
        <div className="space-y-2">
          <div>
            <label className="text-xs text-gray-500 mb-1 block">평가 유형</label>
            <select value={evalType} onChange={(e) => setEvalType(e.target.value)}
              className="w-full text-xs border border-gray-200 rounded px-2 py-1.5">
              {EVAL_TYPE_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">코멘트 (선택)</label>
            <textarea value={comment} onChange={(e) => setComment(e.target.value)}
              placeholder="추가 코멘트를 입력하세요..."
              className="w-full text-xs border border-gray-200 rounded px-2 py-1.5 resize-none h-[72px]" />
          </div>
        </div>
      </div>
      <div className="flex gap-2 mt-3">
        <button onClick={handleSave} disabled={saving}
          className="flex items-center gap-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-xs hover:bg-blue-700 disabled:opacity-50">
          {saving && <Loader2 size={12} className="animate-spin" />} 평가 저장
        </button>
        {lastEvalId && (
          <button onClick={handleUndo}
            className="px-4 py-2 border border-gray-200 text-gray-600 rounded-lg text-xs hover:bg-gray-50">
            되돌리기
          </button>
        )}
      </div>
    </div>
  );
}
