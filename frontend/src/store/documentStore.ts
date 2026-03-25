import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { UploadResult } from "@/types";

interface UploadedDoc {
  file_id: string;
  filename: string;
  total_records: number;
  customer_names: string[];
  records: Record<string, unknown>[];
  saved: boolean;
}

interface DocumentState {
  uploadedDocs: UploadedDoc[];
  activeFileId: string | null;
  addDoc: (result: UploadResult) => void;
  markSaved: (file_id: string) => void;
  removeDoc: (file_id: string) => void;
  setActiveFileId: (id: string | null) => void;
}

export const useDocumentStore = create<DocumentState>()(
  persist(
    (set) => ({
      uploadedDocs: [],
      activeFileId: null,
      addDoc: (result) =>
        set((state) => ({
          uploadedDocs: [
            ...state.uploadedDocs,
            {
              file_id: result.file_id,
              filename: result.filename,
              total_records: result.total_records,
              customer_names: result.customer_names,
              records: result.records,
              saved: false,
            },
          ],
          activeFileId: result.file_id,
        })),
      markSaved: (file_id) =>
        set((state) => ({
          uploadedDocs: state.uploadedDocs.map((d) =>
            d.file_id === file_id ? { ...d, saved: true } : d
          ),
        })),
      removeDoc: (file_id) =>
        set((state) => ({
          uploadedDocs: state.uploadedDocs.filter((d) => d.file_id !== file_id),
          activeFileId:
            state.activeFileId === file_id ? null : state.activeFileId,
        })),
      setActiveFileId: (id) => set({ activeFileId: id }),
    }),
    {
      name: "arisa-documents",
      // records는 용량이 크고 DB에 저장됐으므로 제외 — 메타 정보만 유지
      // 저장 완료된 항목은 로드 시 제거 (새로고침 후에도 남지 않도록)
      partialize: (state) => ({
        uploadedDocs: state.uploadedDocs
          .filter((doc) => !doc.saved)
          .map((doc) => ({
            file_id: doc.file_id,
            filename: doc.filename,
            total_records: doc.total_records,
            customer_names: doc.customer_names,
            records: [] as Record<string, unknown>[],
            saved: false,
          })),
        activeFileId: state.activeFileId,
      }),
    }
  )
);
