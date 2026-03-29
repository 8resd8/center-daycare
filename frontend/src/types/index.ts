// ── 수급자 ──────────────────────────────────────────────────
export interface Customer {
  customer_id: number;
  name: string;
  birth_date: string | null;
  gender: string | null;
  recognition_no: string | null;
  benefit_start_date: string | null;
  grade: string | null;
}

// ── 직원 ────────────────────────────────────────────────────
export interface Employee {
  user_id: number;
  name: string;
  gender: string | null;
  birth_date: string | null;
  work_status: string;
  job_type: string | null;
  hire_date: string | null;
  resignation_date: string | null;
  license_name: string | null;
  license_date: string | null;
}

// ── 일일 기록 ────────────────────────────────────────────────
export interface DailyRecord {
  record_id: number;
  customer_id: number;
  date: string;
  start_time: string | null;
  end_time: string | null;
  total_service_time: string | null;
  transport_service: string | null;
  transport_vehicles: string | null;
  // 신체활동
  hygiene_care: string | null;
  bath_time: string | null;
  bath_method: string | null;
  meal_breakfast: string | null;
  meal_lunch: string | null;
  meal_dinner: string | null;
  toilet_care: string | null;
  mobility_care: string | null;
  physical_note: string | null;
  writer_phy: string | null;
  // 인지관리
  cog_support: string | null;
  comm_support: string | null;
  cognitive_note: string | null;
  writer_cog: string | null;
  // 간호관리
  bp_temp: string | null;
  health_manage: string | null;
  nursing_manage: string | null;
  emergency: string | null;
  nursing_note: string | null;
  writer_nur: string | null;
  // 기능회복
  prog_basic: string | null;
  prog_activity: string | null;
  prog_cognitive: string | null;
  prog_therapy: string | null;
  prog_enhance_detail: string | null;
  functional_note: string | null;
  writer_func: string | null;
}

export interface CustomerWithRecords {
  customer_id: number;
  name: string;
  birth_date: string | null;
  grade: string | null;
  recognition_no: string | null;
  record_count: number;
  first_date: string | null;
  last_date: string | null;
}

// ── 주간 보고서 ──────────────────────────────────────────────
export interface WeeklyReport {
  customer_id: number;
  start_date: string;
  end_date: string;
  report_text: string;
}

export interface WeeklyTableRow {
  주간: string;
  출석일: number;
  "식사량(일반식)": string;
  "식사량(죽식)": string;
  "식사량(다진식)": string;
  소변: string;
  대변: string;
  기저귀교환: string;
}

export interface WeeklyScoreItem {
  label: string;
  prev: number | null;
  curr: number | null;
  diff: number | null;
  trend: string;
}

export interface WeeklyGenerateResult {
  report_text: string;
  weekly_table: WeeklyTableRow[];
  scores: Record<string, WeeklyScoreItem>;
}

export interface ProgEntry {
  date: string;
  detail: string;
}

export interface WeeklyAnalysisResult {
  weekly_table: WeeklyTableRow[];
  scores: Record<string, WeeklyScoreItem>;
  prev_range: [string, string] | null;
  curr_range: [string, string] | null;
  prev_prog_entries: ProgEntry[];
  curr_prog_entries: ProgEntry[];
}

// ── AI 평가 ─────────────────────────────────────────────────
export interface AiEvaluation {
  ai_eval_id: number | null;
  record_id: number;
  category: string;
  oer_fidelity: string | null;
  specificity_score: string | null;
  grammar_score: string | null;
  grade_code: string | null;
  reason_text: string | null;
  suggestion_text: string | null;
  original_text: string | null;
  created_at: string | null;
}

// ── 직원 평가 ────────────────────────────────────────────────
export interface EmployeeEvaluation {
  emp_eval_id: number;
  record_id: number | null;
  target_user_id: number;
  category: string;
  evaluation_type: string;
  evaluation_date: string;
  target_date: string | null;
  evaluator_user_id: number | null;
  score: number;
  comment: string | null;
  target_user_name: string | null;
  evaluator_user_name: string | null;
}

export interface UserDropdownItem {
  user_id: number;
  name: string;
}

// ── 대시보드 ─────────────────────────────────────────────────
export interface DashboardSummary {
  total_customers: number;
  total_records: number;
  total_employees: number;
  avg_grade_score: number | null;
}

export interface EvaluationTrendItem {
  date: string;
  excellent: number;
  average: number;
  improvement: number;
}

export interface EmployeeRankingItem {
  user_id: number;
  name: string;
  total_records: number;
  excellent_count: number;
  average_count: number;
  improvement_count: number;
  score: number;
}

export interface AiGradeDistItem {
  grade: string;
  count: number;
}

export interface EmpEvalTrendItem {
  date: string;
  누락: number;
  내용부족: number;
  오타: number;
  문법: number;
  오류: number;
}

export interface EmpEvalCategoryItem {
  category: string;
  count: number;
}

export interface EmpEvalRankingItem {
  user_id: number;
  name: string;
  total_count: number;
  main_type: string;
}

export interface EmpEvalHistoryRecord {
  emp_eval_id: number;
  evaluation_date: string | null;
  target_date: string | null;
  category: string;
  evaluation_type: string;
  comment: string | null;
  score: number;
}

export interface EmpEvalHistory {
  user_id: number;
  name: string;
  records: EmpEvalHistoryRecord[];
}

// ── 기간 비교 / KPI / 월별 추이 ─────────────────────────────
export interface PeriodData {
  start: string | null;
  end: string | null;
  total: number;
  by_type: Record<string, number>;
}
export interface PeriodComparison {
  current_period: PeriodData;
  previous_period: PeriodData;
  change_rate: number | null;
}
export interface KpiSummary {
  total_issues: number;
  total_issues_prev: number;
  total_issues_delta: number | null;
  avg_per_employee: number | null;
  avg_per_employee_prev: number | null;
  avg_per_employee_delta: number | null;
  high_risk_count: number;
  high_risk_count_prev: number;
  total_employees: number;
}
export interface EmployeeMonthlyTrend {
  month: string;
  count: number;
}

// ── 업로드 ───────────────────────────────────────────────────
export interface UploadResult {
  file_id: string;
  filename: string;
  total_records: number;
  customer_names: string[];
  records: Record<string, unknown>[];
}

// ── 날짜 범위 ────────────────────────────────────────────────
export interface DateRange {
  start: string | null;
  end: string | null;
}
