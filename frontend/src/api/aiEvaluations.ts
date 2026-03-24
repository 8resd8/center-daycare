import api from "./client";
import type { AiEvaluation } from "@/types";

export const aiEvaluationsApi = {
  list: (record_id: number) =>
    api
      .get<AiEvaluation[]>("/ai-evaluations", { params: { record_id } })
      .then((r) => r.data),

  evaluate: (body: {
    record_id: number;
    category: string;
    note_text: string;
    writer_user_id?: number;
  }) =>
    api
      .post<{ grade_code: string; evaluation: unknown }>("/ai-evaluations/evaluate", body)
      .then((r) => r.data),

  evaluateFullRecord: (record_id: number) =>
    api
      .post(`/ai-evaluations/evaluate-record/${record_id}`)
      .then((r) => r.data),
};
