import type { AxiosProgressEvent } from "axios";
import api from "./client";
import type { UploadResult } from "@/types";

export const CHUNK_SIZE = 512 * 1024; // 512 KB

export const uploadApi = {
  // ── 단일 업로드 (기존) ────────────────────────────────────────
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

  // ── 청크 업로드 ──────────────────────────────────────────────
  /** 청크 업로드 세션 초기화 */
  initChunked: (filename: string, totalSize: number, totalChunks: number) =>
    api
      .post<{ upload_id: string; total_chunks: number }>(
        "/upload/chunk/init",
        null,
        { params: { filename, total_size: totalSize, total_chunks: totalChunks } }
      )
      .then((r) => r.data),

  /** 현재까지 업로드된 청크 목록 조회 (이어올리기용) */
  getChunkStatus: (uploadId: string) =>
    api
      .get<{
        upload_id: string;
        done_chunks: number[];
        total_chunks: number;
        filename: string;
      }>(`/upload/chunk/${uploadId}/status`)
      .then((r) => r.data),

  /** 청크 하나 전송 */
  uploadChunk: (
    uploadId: string,
    index: number,
    blob: Blob,
    onProgress?: (e: AxiosProgressEvent) => void
  ) => {
    const form = new FormData();
    form.append("chunk", blob, "chunk.bin");
    return api
      .put<{ upload_id: string; done_chunks: number[]; total_chunks: number }>(
        `/upload/chunk/${uploadId}`,
        form,
        {
          params: { index },
          onUploadProgress: onProgress,
        }
      )
      .then((r) => r.data);
  },

  /** 모든 청크 합치기 → PDF 파싱 트리거 */
  completeChunked: (uploadId: string) =>
    api
      .post<UploadResult>(`/upload/chunk/${uploadId}/complete`)
      .then((r) => r.data),
};
