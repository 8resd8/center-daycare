import { useRef, useState } from "react";
import { CHUNK_SIZE, uploadApi } from "@/api/upload";
import {
  getFileFingerprint,
  useUploadProgressStore,
} from "@/store/uploadProgressStore";
import type { UploadResult } from "@/types";

export type UploadPhase =
  | "idle"
  | "uploading"
  | "parsing"
  | "done"
  | "paused"
  | "error";

export function useChunkedUpload() {
  const [progress, setProgress] = useState(0); // 0–100 (청크 전송 단계)
  const [phase, setPhase] = useState<UploadPhase>("idle");
  const pausedRef = useRef(false);
  const store = useUploadProgressStore();

  const reset = () => {
    setProgress(0);
    setPhase("idle");
    pausedRef.current = false;
  };

  const upload = async (file: File): Promise<UploadResult> => {
    const fingerprint = getFileFingerprint(file);
    const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
    let uploadId: string;
    let startChunk = 0;

    // ── 이어올리기 확인 ────────────────────────────────────────
    const existing = store.getByFingerprint(fingerprint);
    if (existing) {
      try {
        const status = await uploadApi.getChunkStatus(existing.uploadId);
        uploadId = status.upload_id;
        startChunk = status.done_chunks.length;
        store.upsert(fingerprint, { doneChunks: status.done_chunks });
      } catch {
        // 세션 만료(404) → 새 세션
        const init = await uploadApi.initChunked(file.name, file.size, totalChunks);
        uploadId = init.upload_id;
        startChunk = 0;
      }
    } else {
      const init = await uploadApi.initChunked(file.name, file.size, totalChunks);
      uploadId = init.upload_id;
    }

    store.upsert(fingerprint, {
      uploadId,
      totalChunks,
      filename: file.name,
      status: "uploading",
    });
    pausedRef.current = false;
    setPhase("uploading");
    // 이어올리기 시 이미 완료된 청크 진행률 반영
    setProgress(Math.round((startChunk / totalChunks) * 100));

    // ── 청크 전송 루프 ─────────────────────────────────────────
    for (let i = startChunk; i < totalChunks; i++) {
      if (pausedRef.current) {
        store.upsert(fingerprint, { status: "paused" });
        setPhase("paused");
        throw Object.assign(new Error("PAUSED"), { code: "PAUSED" });
      }

      const blob = file.slice(i * CHUNK_SIZE, (i + 1) * CHUNK_SIZE);
      await uploadApi.uploadChunk(uploadId, i, blob, (e) => {
        const sent = e.loaded ?? 0;
        const total = e.total ?? blob.size;
        const chunkProgress = (i + sent / total) / totalChunks;
        setProgress(Math.min(99, Math.round(chunkProgress * 100)));
      });

      const currentDone = store.getByFingerprint(fingerprint)?.doneChunks ?? [];
      store.upsert(fingerprint, { doneChunks: [...currentDone, i] });
    }

    // ── 파싱 단계 ──────────────────────────────────────────────
    setProgress(100);
    setPhase("parsing");
    const result = await uploadApi.completeChunked(uploadId);

    store.remove(fingerprint);
    setPhase("done");
    return result;
  };

  const pause = () => {
    pausedRef.current = true;
  };

  const resume = (file: File) => {
    pausedRef.current = false;
    return upload(file);
  };

  return { upload, pause, resume, progress, phase, reset };
}
