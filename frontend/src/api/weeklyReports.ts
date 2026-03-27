import api from "./client";
import type { WeeklyReport, WeeklyGenerateResult, WeeklyAnalysisResult } from "@/types";

export const weeklyReportsApi = {
  list: (params: {
    customer_id: number;
    start_date?: string;
    end_date?: string;
  }) =>
    api
      .get<WeeklyReport[]>("/weekly-reports", { params })
      .then((r) => r.data),

  generate: (body: {
    customer_id: number;
    start_date: string;
    end_date: string;
  }) =>
    api
      .post<WeeklyGenerateResult>("/weekly-reports/generate", body)
      .then((r) => r.data),

  analysis: (params: {
    customer_id: number;
    start_date: string;
    end_date: string;
  }) =>
    api
      .get<WeeklyAnalysisResult>("/weekly-reports/analysis", { params })
      .then((r) => r.data),

  save: (
    customer_id: number,
    body: { customer_id: number; start_date: string; end_date: string; report_text: string }
  ) =>
    api
      .put<{ message: string }>(`/weekly-reports/${customer_id}`, body)
      .then((r) => r.data),
};
