import api from "./client";
import type { Customer } from "@/types";

export const customersApi = {
  list: (keyword?: string) =>
    api
      .get<Customer[]>("/customers", { params: { keyword } })
      .then((r) => r.data),

  get: (id: number) =>
    api.get<Customer>(`/customers/${id}`).then((r) => r.data),

  create: (data: Omit<Customer, "customer_id">) =>
    api.post<Customer>("/customers", data).then((r) => r.data),

  update: (id: number, data: Omit<Customer, "customer_id">) =>
    api.put<Customer>(`/customers/${id}`, data).then((r) => r.data),

  delete: (id: number) => api.delete(`/customers/${id}`),
};
