import { create } from "zustand";
import { persist } from "zustand/middleware";
import { format, startOfMonth, endOfMonth } from "date-fns";

interface FilterState {
  startDate: string | null;
  endDate: string | null;
  keyword: string;
  workStatus: string;
  selectedCustomerId: number | null;
  setDateRange: (start: string | null, end: string | null) => void;
  setKeyword: (keyword: string) => void;
  setWorkStatus: (status: string) => void;
  setThisMonth: () => void;
  setLastMonth: () => void;
  setSelectedCustomerId: (id: number | null) => void;
}

export const useFilterStore = create<FilterState>()(
  persist(
    (set) => ({
      startDate: format(startOfMonth(new Date()), "yyyy-MM-dd"),
      endDate: format(endOfMonth(new Date()), "yyyy-MM-dd"),
      keyword: "",
      workStatus: "재직",
      selectedCustomerId: null,
      setSelectedCustomerId: (id) => set({ selectedCustomerId: id }),
      setDateRange: (start, end) => set({ startDate: start, endDate: end }),
      setKeyword: (keyword) => set({ keyword }),
      setWorkStatus: (status) => set({ workStatus: status }),
      setThisMonth: () =>
        set({
          startDate: format(startOfMonth(new Date()), "yyyy-MM-dd"),
          endDate: format(endOfMonth(new Date()), "yyyy-MM-dd"),
        }),
      setLastMonth: () => {
        const today = new Date();
        const firstOfThisMonth = startOfMonth(today);
        const lastMonth = new Date(firstOfThisMonth);
        lastMonth.setDate(0);
        set({
          startDate: format(startOfMonth(lastMonth), "yyyy-MM-dd"),
          endDate: format(lastMonth, "yyyy-MM-dd"),
        });
      },
    }),
    {
      name: "arisa-filter",
      // 함수는 직렬화 불가 → 날짜/ID 값만 저장
      partialize: (state) => ({
        startDate: state.startDate,
        endDate: state.endDate,
        selectedCustomerId: state.selectedCustomerId,
        workStatus: state.workStatus,
      }),
    }
  )
);
