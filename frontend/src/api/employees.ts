import api from "./client";
import type { Employee } from "@/types";

export const employeesApi = {
  list: (params?: { keyword?: string; work_status?: string }) =>
    api.get<Employee[]>("/employees", { params }).then((r) => r.data),

  get: (id: number) =>
    api.get<Employee>(`/employees/${id}`).then((r) => r.data),

  create: (
    data: Omit<Employee, "user_id"> & { username: string; password: string }
  ) => api.post<Employee>("/employees", data).then((r) => r.data),

  update: (id: number, data: Omit<Employee, "user_id">) =>
    api.put<Employee>(`/employees/${id}`, data).then((r) => r.data),

  softDelete: (id: number) => api.delete(`/employees/${id}`),
};
