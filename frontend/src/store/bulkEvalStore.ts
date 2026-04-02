import { create } from "zustand";

type BulkEvalStore = {
  /** item.id → emp_eval_id (등록된 항목) */
  registeredItems: Map<string, number>;
  register: (itemId: string, evalId: number) => void;
  unregister: (itemId: string) => void;
  clear: () => void;
};

export const useBulkEvalStore = create<BulkEvalStore>((set) => ({
  registeredItems: new Map(),
  register: (itemId, evalId) =>
    set((s) => {
      const next = new Map(s.registeredItems);
      next.set(itemId, evalId);
      return { registeredItems: next };
    }),
  unregister: (itemId) =>
    set((s) => {
      const next = new Map(s.registeredItems);
      next.delete(itemId);
      return { registeredItems: next };
    }),
  clear: () => set({ registeredItems: new Map() }),
}));
