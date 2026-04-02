import { useQueries } from "@tanstack/react-query";
import { useMemo } from "react";
import { dailyRecordsApi } from "@/api/dailyRecords";
import { useFilterStore } from "@/store/filterStore";
import type { DailyRecord, CustomerWithRecords } from "@/types";

/**
 * 전체 수급자의 일일 기록을 병렬 조회한다.
 * 캐시 키는 CareRecordsPage의 기존 쿼리와 동일하여 중복 API 요청이 발생하지 않는다.
 */
export function useAllCustomerRecords(customers: CustomerWithRecords[]): {
  allRecords: Map<number, DailyRecord[]>;
  isLoading: boolean;
} {
  const { startDate, endDate } = useFilterStore();

  const results = useQueries({
    queries: customers.map((c) => ({
      queryKey: ["daily-records", c.customer_id, startDate, endDate] as const,
      queryFn: () =>
        dailyRecordsApi.list({
          customer_id: c.customer_id,
          start_date: startDate ?? undefined,
          end_date: endDate ?? undefined,
        }),
      enabled: !!startDate && !!endDate && customers.length > 0,
    })),
  });

  const allRecords = useMemo(() => {
    const map = new Map<number, DailyRecord[]>();
    customers.forEach((c, i) => {
      const data = results[i]?.data;
      if (data) map.set(c.customer_id, data);
    });
    return map;
  }, [customers, results]);

  const isLoading = results.some((r) => r.isLoading);

  return { allRecords, isLoading };
}
