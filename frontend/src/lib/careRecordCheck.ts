// frontend/src/lib/careRecordCheck.ts
import type { DailyRecord } from "@/types";

export function checkRecord(r: DailyRecord) {
  const absent = ["미이용", "결석", "일정없음"].includes((r.total_service_time ?? "").trim());
  const endHour = r.end_time ? parseInt(r.end_time.split(":")[0] ?? "0") : 0;
  const endMin = r.end_time ? parseInt(r.end_time.split(":")[1] ?? "0") : 0;
  const isAfternoon = endHour > 17 || (endHour === 17 && endMin >= 10);
  const mk = (v: string | null | undefined) => absent ? null : !!v?.trim();
  return {
    date: r.date,
    basic: { 총시간: mk(r.total_service_time), 시작시간: mk(r.start_time), 종료시간: mk(r.end_time), 이동서비스: mk(r.transport_service), 차량번호: mk(r.transport_vehicles), writer: r.writer_phy ?? "" },
    physical: { 청결: mk(r.hygiene_care), 점심: mk(r.meal_lunch), 저녁: absent ? null : (isAfternoon ? !!r.meal_dinner?.trim() : null), 화장실: mk(r.toilet_care), 이동도움: mk(r.mobility_care), 특이사항: mk(r.physical_note), writer: r.writer_phy ?? "" },
    cognitive: { 인지관리: mk(r.cog_support), 의사소통: mk(r.comm_support), 특이사항: mk(r.cognitive_note), writer: r.writer_cog ?? "" },
    nursing: { "혈압/체온": mk(r.bp_temp), 건강관리: mk(r.health_manage), 특이사항: mk(r.nursing_note), writer: r.writer_nur ?? "" },
    recovery: { 향상프로그램: mk(r.prog_basic), 일상생활훈련: mk(r.prog_activity), 인지활동프로그램: mk(r.prog_cognitive), 인지기능향상: mk(r.prog_therapy), 특이사항: mk(r.functional_note), writer: r.writer_func ?? "" },
  };
}

export type CheckResult = ReturnType<typeof checkRecord>;
export type CheckCategory = "basic" | "physical" | "cognitive" | "nursing" | "recovery";

export function calcRate(results: CheckResult[], cat: CheckCategory) {
  let total = 0, done = 0;
  for (const r of results) {
    const checks = r[cat] as Record<string, boolean | null | string>;
    for (const [k, v] of Object.entries(checks)) {
      if (k === "writer" || v === null) continue;
      total++;
      if (v) done++;
    }
  }
  return total === 0 ? 100 : Math.round((done / total) * 1000) / 10;
}
