import api from "./client";
import type { FeedbackReport, FeedbackReportMonthItem } from "@/types";

export const feedbackReportsApi = {
  generate: (user_id: number, target_month: string, admin_note?: string | null) =>
    api
      .post<FeedbackReport>(`/dashboard/employee/${user_id}/feedback-report`, {
        target_month,
        admin_note: admin_note || null,
      })
      .then((r) => r.data),

  listMonths: (user_id: number) =>
    api
      .get<FeedbackReportMonthItem[]>(`/dashboard/employee/${user_id}/feedback-reports`)
      .then((r) => r.data),

  getByMonth: (user_id: number, month: string) =>
    api
      .get<FeedbackReport>(`/dashboard/employee/${user_id}/feedback-report/${month}`)
      .then((r) => r.data),
};
