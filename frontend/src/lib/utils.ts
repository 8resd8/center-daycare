import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "-";
  return dateStr.slice(0, 10);
}

export function getGradeBadgeClass(grade: string | null | undefined): string {
  switch (grade) {
    case "우수":
      return "bg-green-100 text-green-800";
    case "평균":
      return "bg-yellow-100 text-yellow-800";
    case "개선":
      return "bg-red-100 text-red-800";
    default:
      return "bg-gray-100 text-gray-600";
  }
}
