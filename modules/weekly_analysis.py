from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from statistics import mean
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .parsing_database import get_db_connection

POSITIVE_KEYWORDS = ["개선", "안정", "호전", "유지", "활발", "양호", "미흡하지않음"]
NEGATIVE_KEYWORDS = ["악화", "저하", "불안", "통증", "문제", "감소", "주의", "거부", "통증"]
HIGHLIGHT_KEYWORDS = ["통증", "거부", "증가", "감소", "악화", "호전", "불안", "주의", "사고"]
MEAL_TYPES = ["일반식", "죽식", "다짐식", "경관식", "연식", "특식"]
MEAL_AMOUNT_RULES = [
    (["전량", "정량", "완", "모두", "잘"], (1.0, "전량")),
    (["절반", "1/2", "반", "50%", "이하"], (0.5, "1/2이하")),
    (["거부", "못", "불가", "0%"], (0.0, "거부")),
]
CATEGORIES = {
    "physical": ("physical_note", "신체활동"),
    "cognitive": ("cognitive_note", "인지관리"),
    "nursing": ("nursing_note", "간호관리"),
    "functional": ("functional_note", "기능회복"),
}


def _score_text(text: Optional[str]) -> int:
    if not text:
        return 50
    normalized = text.replace(" ", "")
    score = 50
    for kw in POSITIVE_KEYWORDS:
        if kw in normalized:
            score += 5
    for kw in NEGATIVE_KEYWORDS:
        if kw in normalized:
            score -= 5
    return max(0, min(100, score))


def _fetch_two_week_records(
    name: str, start_date: date
) -> Tuple[List[Dict,], Tuple[date, date], Tuple[date, date]]:
    prev_start = start_date - timedelta(days=7)
    prev_end = start_date - timedelta(days=1)
    curr_end = start_date + timedelta(days=6)

    query = """
        SELECT
            di.date,
            dp.note AS physical_note,
            dc.note AS cognitive_note,
            dn.note AS nursing_note,
            dr.note AS functional_note,
            dp.meal_breakfast,
            dp.meal_lunch,
            dp.meal_dinner,
            dp.toilet_care,
            dp.bath_time,
            dn.bp_temp,
            dr.prog_therapy
        FROM daily_infos di
        JOIN customers c ON c.customer_id = di.customer_id
        LEFT JOIN daily_physicals dp ON dp.record_id = di.record_id
        LEFT JOIN daily_cognitives dc ON dc.record_id = di.record_id
        LEFT JOIN daily_nursings dn ON dn.record_id = di.record_id
        LEFT JOIN daily_recoveries dr ON dr.record_id = di.record_id
        WHERE c.name = %s AND di.date BETWEEN %s AND %s
        ORDER BY di.date
    """

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, (name, prev_start, curr_end))
        rows = cursor.fetchall()
        return rows, (prev_start, prev_end), (start_date, curr_end)
    finally:
        cursor.close()
        conn.close()


def compute_weekly_status(customer_name: str, week_start_str: str) -> Dict:
    try:
        week_start = datetime.strptime(week_start_str, "%Y-%m-%d").date()
    except Exception:
        return {"error": "날짜 형식이 올바르지 않습니다."}

    try:
        rows, prev_range, curr_range = _fetch_two_week_records(customer_name, week_start)
    except Exception as e:
        return {"error": str(e)}

    if not rows:
        return {"data": [], "ranges": (prev_range, curr_range), "scores": {}}

    buckets: Dict[str, Dict[str, List[int]]] = {
        "prev": defaultdict(list),
        "curr": defaultdict(list),
    }

    for row in rows:
        record_date = row["date"]
        bucket = "curr" if record_date >= week_start else "prev"
        for key, (field, _) in CATEGORIES.items():
            buckets[bucket][key].append(_score_text(row.get(field)))

    def _avg(values: List[int]) -> Optional[float]:
        return round(mean(values), 1) if values else None

    scores = {}
    for key, (_, label) in CATEGORIES.items():
        prev_score = _avg(buckets["prev"].get(key, []))
        curr_score = _avg(buckets["curr"].get(key, []))
        if prev_score is None and curr_score is None:
            continue
        diff = None
        trend = "변화 없음"
        if prev_score is not None and curr_score is not None:
            diff = round(curr_score - prev_score, 1)
            if diff > 1:
                trend = "상승 ⬆️"
            elif diff < -1:
                trend = "하락 ⬇️"
        elif curr_score is not None:
            trend = "신규 데이터"
        scores[key] = {
            "label": label,
            "prev": prev_score,
            "curr": curr_score,
            "diff": diff,
            "trend": trend,
        }

    trend = analyze_weekly_trend(rows, prev_range, curr_range)

    return {
        "ranges": (prev_range, curr_range),
        "scores": scores,
        "raw": rows,
        "trend": trend,
    }


def _detect_meal_type(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    for t in MEAL_TYPES:
        if t in text:
            return t
    return None


def _score_meal_amount(text: Optional[str]) -> float:
    if not text:
        return 0.75
    for keywords, (score, _) in MEAL_AMOUNT_RULES:
        if any(k in text for k in keywords):
            return score
    return 0.75


def _meal_amount_label(text: Optional[str]) -> str:
    if not text:
        return "정보없음"
    for keywords, (_, label) in MEAL_AMOUNT_RULES:
        if any(k in text for k in keywords):
            return label
    return "정보없음"


def _extract_toilet_count(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    matches = re.findall(r"(\d+)\s*회", text)
    if matches:
        nums = [int(n) for n in matches]
        return sum(nums)
    digits = re.findall(r"\d+", text)
    if digits:
        return float(digits[0])
    return None


def _parse_toilet_breakdown(text: Optional[str]) -> Dict[str, float]:
    if not text:
        return {}
    detail = {"stool": 0.0, "urine": 0.0, "diaper": 0.0}
    stool_matches = re.findall(r"(대변|배변)\s*(\d+)\s*회", text)
    urine_matches = re.findall(r"(소변|배뇨)\s*(\d+)\s*회", text)
    diaper_matches = re.findall(r"(기저귀|교환)\s*(\d+)\s*회", text)
    for _, n in stool_matches:
        detail["stool"] += float(n)
    for _, n in urine_matches:
        detail["urine"] += float(n)
    for _, n in diaper_matches:
        detail["diaper"] += float(n)
    return detail


def _summarize_meal_details(df: pd.DataFrame) -> str:
    if df.empty:
        return "-"
    details = []
    for _, row in df.sort_values("date").iterrows():
        detail = row.get("meal_detail")
        if detail:
            details.append(detail)
    return " / ".join(details) if details else "-"


def _summarize_toilet_summary(df: pd.DataFrame) -> str:
    if df.empty:
        return "-"
    total = {"stool": 0.0, "urine": 0.0, "diaper": 0.0}
    for detail_map in df["toilet_detail"]:
        if isinstance(detail_map, dict):
            for key in total:
                total[key] += detail_map.get(key, 0.0)
    if not any(total.values()):
        return "-"
    return (
        f"대변{int(total['stool'])}회/소변{int(total['urine'])}회 "
        f"(기저귀교환{int(total['diaper'])}회)"
    )


def _merge_notes(df: pd.DataFrame, highlight: bool = False) -> List[str]:
    notes = []
    for _, row in df.iterrows():
        parts = []
        if row.get("physical_note"):
            parts.append(f"신체: {row['physical_note']}")
        if row.get("cognitive_note"):
            parts.append(f"인지: {row['cognitive_note']}")
        if row.get("nursing_note"):
            parts.append(f"간호: {row['nursing_note']}")
        if row.get("functional_note"):
            parts.append(f"기능: {row['functional_note']}")
        if not parts:
            continue
        line = f"[{row['date'].strftime('%m-%d')}] " + " / ".join(parts)
        if highlight:
            for kw in HIGHLIGHT_KEYWORDS:
                if kw in line:
                    line = line.replace(
                        kw, f"<span style='background-color:#fff3cd;'>{kw}</span>"
                    )
        notes.append(line)
    return notes


def analyze_weekly_trend(
    rows: List[Dict], prev_range: Tuple[date, date], curr_range: Tuple[date, date]
) -> Dict:
    if not rows:
        return {}
    df = pd.DataFrame(rows)
    if df.empty:
        return {}
    df["date"] = pd.to_datetime(df["date"]).dt.date

    def _derive(row):
        meals = [row.get("meal_breakfast"), row.get("meal_lunch"), row.get("meal_dinner")]
        meal_types = [t for t in (_detect_meal_type(m) for m in meals) if t]
        meal_type = meal_types[0] if meal_types else "미확인"
        meal_scores = [_score_meal_amount(m or "") for m in meals if m is not None]
        meal_amount_score = round(sum(meal_scores) / len(meal_scores), 2) if meal_scores else 0.0
        meal_detail = []
        for meal_text in meals:
            if not meal_text:
                continue
            meal_detail.append(f"{_detect_meal_type(meal_text) or '미확인'} ({_meal_amount_label(meal_text)})")
        toilet_count = _extract_toilet_count(row.get("toilet_care"))
        toilet_detail = _parse_toilet_breakdown(row.get("toilet_care"))
        return pd.Series(
            {
                "meal_type": meal_type,
                "meal_amount_score": meal_amount_score,
                "toilet_count": toilet_count,
                "note_phy": row.get("physical_note"),
                "note_nur": row.get("nursing_note"),
                "meal_detail": " / ".join(meal_detail),
                "toilet_detail": toilet_detail,
            }
        )

    derived = df.apply(_derive, axis=1)
    df = pd.concat([df, derived], axis=1)

    prev_start, prev_end = prev_range
    curr_start, curr_end = curr_range
    last_week_df = df[
        (df["date"] >= prev_start)
        & (df["date"] <= prev_end)
    ]
    this_week_df = df[
        (df["date"] >= curr_start)
        & (df["date"] <= curr_end)
    ]

    def _mode(series: pd.Series) -> str:
        if series.empty:
            return "-"
        mode = series.mode()
        return mode.iloc[0] if not mode.empty else "-"

    last_type = _mode(last_week_df["meal_type"])
    this_type = _mode(this_week_df["meal_type"])
    last_score = round(last_week_df["meal_amount_score"].mean(), 2) if not last_week_df.empty else 0.0
    this_score = round(this_week_df["meal_amount_score"].mean(), 2) if not this_week_df.empty else 0.0

    def _score_trend(prev, curr):
        diff = curr - prev
        if diff > 0.2:
            return "증가 📈"
        if diff < -0.2:
            return "감소 📉"
        return "유지 -"

    last_toilet = last_week_df["toilet_count"].mean() if not last_week_df.empty else 0.0
    this_toilet = this_week_df["toilet_count"].mean() if not this_week_df.empty else 0.0

    header = {
        "meal_amount": {
            "label": "식사량",
            "trend": _score_trend(last_score, this_score),
            "values": (last_score * 100, this_score * 100),
        },
        "toilet": {
            "label": "배설",
            "trend": "증가 ⚠️" if this_toilet > last_toilet + 1 else ("감소" if this_toilet + 1 < last_toilet else "유지"),
            "values": (last_toilet, this_toilet),
        },
        "meal_type": {
            "label": "식사 형태",
            "change": f"{last_type} → {this_type}" if last_type != this_type else last_type,
            "changed": last_type != this_type,
        },
    }

    notes = {
        "last": _merge_notes(last_week_df),
        "this": _merge_notes(this_week_df, highlight=True),
    }

    meal_detail_summary = {
        "last": _summarize_meal_details(last_week_df),
        "this": _summarize_meal_details(this_week_df),
    }
    toilet_detail_summary = {
        "last": _summarize_toilet_summary(last_week_df),
        "this": _summarize_toilet_summary(this_week_df),
    }

    category_notes = {}
    for key, (field, label) in CATEGORIES.items():
        vals = [
            f"[{row['date'].strftime('%m-%d')}] {row[field]}"
            for _, row in this_week_df.iterrows()
            if row.get(field)
        ]
        category_notes[key] = {"label": label, "entries": vals}

    def _latest_text_value(source_df: pd.DataFrame, column: str) -> str:
        if source_df.empty or column not in source_df:
            return "-"
        values = [
            str(value).strip()
            for value in source_df[column]
            if value is not None and str(value).strip()
        ]
        return values[-1] if values else "-"

    MEAL_TYPE_KEYWORDS = {
        "일반식": ["일반식"],
        "죽식": ["죽식"],
        "다진식": ["다진식", "다짐식"],
    }

    MEAL_PORTION_MAP = {
        "1/2이상": 0.75,
        "1/2 이상": 0.75,
        "1/2이하": 0.25,
        "1/2 이하": 0.25,
        "정량": 1.0,
        "전량": 1.0,
        "완식": 1.0,
    }

    def _extract_meal_type_amounts(text: Optional[str]) -> Dict[str, float]:
        totals = {key: 0.0 for key in MEAL_TYPE_KEYWORDS}
        if not text:
            return totals
        segments = [seg.strip() for seg in re.split(r"[\/,]", text) if seg.strip()]
        for segment in segments:
            ratio = 0.5
            for keyword, value in MEAL_PORTION_MAP.items():
                if keyword in segment:
                    ratio = value
                    break
            matched = False
            for type_label, keywords in MEAL_TYPE_KEYWORDS.items():
                if any(keyword in segment for keyword in keywords):
                    totals[type_label] += ratio
                    matched = True
            if not matched and "일반식" in segment:
                totals["일반식"] += ratio
        return totals

    def _average_toilet_breakdown(source_df: pd.DataFrame) -> Optional[Dict[str, float]]:
        if source_df.empty:
            return None
        total = {"stool": 0.0, "urine": 0.0, "diaper": 0.0}
        count = 0
        for detail in source_df.get("toilet_detail", []):
            if not isinstance(detail, dict):
                continue
            count += 1
            for key in total:
                total[key] += detail.get(key, 0.0)
        if count == 0:
            return None
        return {key: round(total[key] / count, 1) for key in total}

    def _format_toilet_value(detail: Optional[Dict[str, float]], key: str) -> str:
        if not detail:
            return "-"
        value = detail.get(key)
        if value is None:
            return "-"
        if float(value).is_integer():
            formatted = f"{int(value)}"
        else:
            formatted = f"{value:.1f}"
        return f"{formatted}회"

    def _sum_toilet_counts(source_df: pd.DataFrame) -> Dict[str, float]:
        total = {"stool": 0.0, "urine": 0.0, "diaper": 0.0}
        for detail in source_df.get("toilet_detail", []):
            if not isinstance(detail, dict):
                continue
            for key in total:
                total[key] += detail.get(key, 0.0)
        return total

    def _format_total(value: float) -> str:
        if value is None:
            return "-"
        if float(value).is_integer():
            return f"{int(value)}"
        return f"{value:.1f}"

    def _sum_meals(source_df: pd.DataFrame) -> Dict[str, float]:
        totals = {key: 0.0 for key in MEAL_TYPE_KEYWORDS}
        meal_fields = ["meal_breakfast", "meal_lunch", "meal_dinner"]
        for _, row in source_df.iterrows():
            for field in meal_fields:
                parsed = _extract_meal_type_amounts(row.get(field))
                for meal_type, value in parsed.items():
                    totals[meal_type] += value
        return totals

    last_toilet_totals = _sum_toilet_counts(last_week_df)
    this_toilet_totals = _sum_toilet_counts(this_week_df)
    last_meals = _sum_meals(last_week_df)
    this_meals = _sum_meals(this_week_df)

    weekly_table = [
        {
            "주간": "저번주",
            "식사량(일반식)": _format_total(last_meals["일반식"]),
            "식사량(죽식)": _format_total(last_meals["죽식"]),
            "식사량(다진식)": _format_total(last_meals["다진식"]),
            "소변": f"{_format_total(last_toilet_totals['urine'])}회",
            "대변": f"{_format_total(last_toilet_totals['stool'])}회",
            "기저기교환": f"{_format_total(last_toilet_totals['diaper'])}회",
        },
        {
            "주간": "이번주",
            "식사량(일반식)": _format_total(this_meals["일반식"]),
            "식사량(죽식)": _format_total(this_meals["죽식"]),
            "식사량(다진식)": _format_total(this_meals["다진식"]),
            "소변": f"{_format_total(this_toilet_totals['urine'])}회",
            "대변": f"{_format_total(this_toilet_totals['stool'])}회",
            "기저기교환": f"{_format_total(this_toilet_totals['diaper'])}회",
        },
    ]

    return {
        "header": header,
        "notes": notes,
        "meal_detail": meal_detail_summary,
        "toilet_detail": toilet_detail_summary,
        "weekly_table": weekly_table,
        "category_notes": category_notes,
    }
