import api from "./client";
import type { UploadResult } from "@/types";

export const uploadApi = {
  upload: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return api
      .post<UploadResult>("/upload", formData)
      .then((r) => r.data);
  },

  save: (file_id: string) =>
    api
      .post<{ saved_count: number; message: string }>(`/upload/${file_id}/save`)
      .then((r) => r.data),

  preview: (file_id: string) =>
    api.get(`/upload/${file_id}/preview`).then((r) => r.data),
};
