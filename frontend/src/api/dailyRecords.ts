import api from "./client";
import type { DailyRecord, CustomerWithRecords } from "@/types";

export const dailyRecordsApi = {
  list: (params: {
    customer_id: number;
    start_date?: string;
    end_date?: string;
  }) =>
    api
      .get<DailyRecord[]>("/daily-records", { params })
      .then((r) => r.data),

  get: (id: number) =>
    api.get<DailyRecord>(`/daily-records/${id}`).then((r) => r.data),

  customersWithRecords: (params?: { start_date?: string; end_date?: string }) =>
    api
      .get<CustomerWithRecords[]>("/daily-records/customers-with-records", {
        params,
      })
      .then((r) => r.data),

  delete: (id: number) => api.delete(`/daily-records/${id}`),
};
