import api from "./client";
import type { EmployeeEvaluation, UserDropdownItem } from "@/types";

export const employeeEvaluationsApi = {
  users: () =>
    api
      .get<UserDropdownItem[]>("/employee-evaluations/users")
      .then((r) => r.data),

  list: (record_id: number) =>
    api
      .get<EmployeeEvaluation[]>("/employee-evaluations", {
        params: { record_id },
      })
      .then((r) => r.data),

  create: (body: Omit<EmployeeEvaluation, "emp_eval_id" | "target_user_name" | "evaluator_user_name">) =>
    api
      .post<EmployeeEvaluation>("/employee-evaluations", body)
      .then((r) => r.data),

  update: (id: number, body: Partial<EmployeeEvaluation>) =>
    api
      .put<{ message: string }>(`/employee-evaluations/${id}`, body)
      .then((r) => r.data),

  delete: (id: number) => api.delete(`/employee-evaluations/${id}`),
};
