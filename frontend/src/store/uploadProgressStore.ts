import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface UploadSession {
  uploadId: string;
  totalChunks: number;
  doneChunks: number[];
  filename: string;
  status: "uploading" | "paused" | "done" | "error";
}

interface UploadProgressState {
  sessions: Record<string, UploadSession>; // key = fingerprint
  upsert: (fingerprint: string, session: Partial<UploadSession>) => void;
  remove: (fingerprint: string) => void;
  getByFingerprint: (fp: string) => UploadSession | undefined;
}

export const useUploadProgressStore = create<UploadProgressState>()(
  persist(
    (set, get) => ({
      sessions: {},
      upsert: (fingerprint, partial) =>
        set((state) => ({
          sessions: {
            ...state.sessions,
            [fingerprint]: {
              ...(state.sessions[fingerprint] ?? {
                uploadId: "",
                totalChunks: 0,
                doneChunks: [],
                filename: "",
                status: "uploading" as const,
              }),
              ...partial,
            },
          },
        })),
      remove: (fingerprint) =>
        set((state) => {
          const next = { ...state.sessions };
          delete next[fingerprint];
          return { sessions: next };
        }),
      getByFingerprint: (fp) => get().sessions[fp],
    }),
    { name: "arisa-upload-progress" }
  )
);

export function getFileFingerprint(file: File): string {
  return `${file.name}|${file.size}|${file.lastModified}`;
}
