import api from "./client";
import type {
  DashboardSummary,
  EvaluationTrendItem,
  EmployeeRankingItem,
  AiGradeDistItem,
  EmpEvalTrendItem,
  EmpEvalCategoryItem,
  EmpEvalRankingItem,
  EmpEvalHistory,
  PeriodComparison,
  KpiSummary,
  EmployeeMonthlyTrend,
} from "@/types";

const params = (start_date?: string, end_date?: string) =>
  start_date && end_date ? { start_date, end_date } : {};

export const dashboardApi = {
  summary: (start_date?: string, end_date?: string) =>
    api
      .get<DashboardSummary>("/dashboard/summary", {
        params: params(start_date, end_date),
      })
      .then((r) => r.data),

  trend: (start_date?: string, end_date?: string) =>
    api
      .get<EvaluationTrendItem[]>("/dashboard/evaluation-trend", {
        params: params(start_date, end_date),
      })
      .then((r) => r.data),

  rankings: (start_date?: string, end_date?: string) =>
    api
      .get<EmployeeRankingItem[]>("/dashboard/employee-rankings", {
        params: params(start_date, end_date),
      })
      .then((r) => r.data),

  gradeDist: (start_date?: string, end_date?: string) =>
    api
      .get<AiGradeDistItem[]>("/dashboard/ai-grade-dist", {
        params: params(start_date, end_date),
      })
      .then((r) => r.data),

  employeeDetails: (user_id: number, start_date?: string, end_date?: string) =>
    api
      .get(`/dashboard/employee/${user_id}/details`, {
        params: params(start_date, end_date),
      })
      .then((r) => r.data),

  empEvalTrend: (start_date?: string, end_date?: string) =>
    api
      .get<EmpEvalTrendItem[]>("/dashboard/emp-eval-trend", {
        params: params(start_date, end_date),
      })
      .then((r) => r.data),

  empEvalCategory: (start_date?: string, end_date?: string) =>
    api
      .get<EmpEvalCategoryItem[]>("/dashboard/emp-eval-category", {
        params: params(start_date, end_date),
      })
      .then((r) => r.data),

  empEvalRankings: (start_date?: string, end_date?: string) =>
    api
      .get<EmpEvalRankingItem[]>("/dashboard/emp-eval-rankings", {
        params: params(start_date, end_date),
      })
      .then((r) => r.data),

  empEvalHistory: (user_id: number, start_date?: string, end_date?: string) =>
    api
      .get<EmpEvalHistory>(`/dashboard/employee/${user_id}/emp-eval-history`, {
        params: params(start_date, end_date),
      })
      .then((r) => r.data),

  periodComparison: (start_date?: string, end_date?: string) =>
    api
      .get<PeriodComparison>("/dashboard/period-comparison", {
        params: params(start_date, end_date),
      })
      .then((r) => r.data),

  kpiSummary: (start_date?: string, end_date?: string) =>
    api
      .get<KpiSummary>("/dashboard/kpi-summary", {
        params: params(start_date, end_date),
      })
      .then((r) => r.data),

  employeeMonthlyTrend: (user_id: number, months?: number) =>
    api
      .get<EmployeeMonthlyTrend[]>(
        `/dashboard/employee/${user_id}/monthly-trend`,
        { params: months ? { months } : {} }
      )
      .then((r) => r.data),
};
