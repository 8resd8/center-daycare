"""대시보드 라우터"""

from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from datetime import date, timedelta

from backend.dependencies import get_current_user
from backend.encryption import EncryptionService, mask_name, is_admin

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/dashboard/summary")
def get_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """KPI 요약"""
    from modules.db_connection import db_query

    with db_query() as cursor:
        cursor.execute("SELECT COUNT(*) as cnt FROM customers")
        total_customers = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE work_status = '재직'")
        total_employees = cursor.fetchone()["cnt"]

        if start_date and end_date:
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM daily_infos WHERE date BETWEEN %s AND %s",
                (start_date, end_date),
            )
        else:
            cursor.execute("SELECT COUNT(*) as cnt FROM daily_infos")
        total_records = cursor.fetchone()["cnt"]

        if start_date and end_date:
            cursor.execute(
                """
                SELECT AVG(CASE grade_code
                    WHEN '우수' THEN 3
                    WHEN '평균' THEN 2
                    WHEN '개선' THEN 1
                    ELSE NULL
                END) as avg_score
                FROM ai_evaluations ae
                JOIN daily_infos di ON ae.record_id = di.record_id
                WHERE di.date BETWEEN %s AND %s
                """,
                (start_date, end_date),
            )
        else:
            cursor.execute(
                """
                SELECT AVG(CASE grade_code
                    WHEN '우수' THEN 3
                    WHEN '평균' THEN 2
                    WHEN '개선' THEN 1
                    ELSE NULL
                END) as avg_score
                FROM ai_evaluations
                """
            )
        avg_row = cursor.fetchone()
        avg_score = round(avg_row["avg_score"], 2) if avg_row and avg_row["avg_score"] else None

    return {
        "total_customers": total_customers,
        "total_records": total_records,
        "total_employees": total_employees,
        "avg_grade_score": avg_score,
    }


@router.get("/dashboard/evaluation-trend")
def get_evaluation_trend(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """날짜별 평가 등급 추이"""
    from modules.db_connection import db_query

    params = []
    where = ""
    if start_date and end_date:
        where = "WHERE di.date BETWEEN %s AND %s"
        params = [start_date, end_date]

    query = f"""
        SELECT
            di.date as eval_date,
            SUM(CASE ae.grade_code WHEN '우수' THEN 1 ELSE 0 END) as excellent,
            SUM(CASE ae.grade_code WHEN '평균' THEN 1 ELSE 0 END) as average,
            SUM(CASE ae.grade_code WHEN '개선' THEN 1 ELSE 0 END) as improvement
        FROM ai_evaluations ae
        JOIN daily_infos di ON ae.record_id = di.record_id
        {where}
        GROUP BY di.date
        ORDER BY di.date
    """
    with db_query() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()

    return [
        {
            "date": str(r["eval_date"]),
            "excellent": r["excellent"],
            "average": r["average"],
            "improvement": r["improvement"],
        }
        for r in rows
    ]


@router.get("/dashboard/employee-rankings")
def get_employee_rankings(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """직원별 기록 및 평가 랭킹"""
    from modules.db_connection import db_query

    enc = EncryptionService()
    admin = is_admin(current_user)

    # 1단계: 재직 중 직원 조회 및 이름 복호화
    with db_query() as cursor:
        cursor.execute("SELECT user_id, name FROM users WHERE work_status = '재직'")
        users = cursor.fetchall()

    date_params: list = []
    date_filter = ""
    if start_date and end_date:
        date_filter = "AND di.date BETWEEN %s AND %s"
        date_params = [start_date, end_date]

    result = []
    for u in users:
        uid = u["user_id"]
        decrypted_name = enc.safe_decrypt(u["name"])

        # 2단계: 복호화된 이름으로 writer_name(평문) 매칭
        params = [decrypted_name, decrypted_name] + date_params
        query = f"""
            SELECT
                COUNT(DISTINCT di.record_id) as total_records,
                SUM(CASE ae.grade_code WHEN '우수' THEN 1 ELSE 0 END) as excellent_count,
                SUM(CASE ae.grade_code WHEN '평균' THEN 1 ELSE 0 END) as average_count,
                SUM(CASE ae.grade_code WHEN '개선' THEN 1 ELSE 0 END) as improvement_count
            FROM daily_infos di
            LEFT JOIN ai_evaluations ae ON ae.record_id = di.record_id
            WHERE di.record_id IN (
                SELECT dp.record_id FROM daily_physicals dp WHERE dp.writer_name = %s
                UNION
                SELECT dc.record_id FROM daily_cognitives dc WHERE dc.writer_name = %s
            ) {date_filter}
        """
        with db_query() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()

        exc = (row["excellent_count"] or 0) if row else 0
        avg = (row["average_count"] or 0) if row else 0
        imp = (row["improvement_count"] or 0) if row else 0
        total_r = (row["total_records"] or 0) if row else 0
        total_grade = exc + avg + imp
        score = ((exc * 3 + avg * 2 + imp) / total_grade) if total_grade > 0 else 0.0

        display_name = decrypted_name if admin else mask_name(decrypted_name)
        result.append({
            "user_id": uid,
            "name": display_name,
            "total_records": total_r,
            "excellent_count": exc,
            "average_count": avg,
            "improvement_count": imp,
            "score": round(score, 2),
        })

    result.sort(key=lambda x: (-x["excellent_count"], -x["total_records"]))
    return result


@router.get("/dashboard/ai-grade-dist")
def get_ai_grade_dist(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """AI 평가 등급 분포"""
    from modules.db_connection import db_query

    params = []
    where = ""
    if start_date and end_date:
        where = "WHERE di.date BETWEEN %s AND %s"
        params = [start_date, end_date]

    query = f"""
        SELECT ae.grade_code as grade, COUNT(*) as count
        FROM ai_evaluations ae
        JOIN daily_infos di ON ae.record_id = di.record_id
        {where}
        GROUP BY ae.grade_code
    """
    with db_query() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()

    return [{"grade": r["grade"], "count": r["count"]} for r in rows]


@router.get("/dashboard/employee/{user_id}/details")
def get_employee_details(
    user_id: int,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """직원별 상세 기록 및 평가"""
    from modules.db_connection import db_query

    enc = EncryptionService()
    admin = is_admin(current_user)

    with db_query() as cursor:
        cursor.execute("SELECT user_id, name FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="직원을 찾을 수 없습니다.")

    decrypted_name = enc.safe_decrypt(user["name"])

    params = [decrypted_name, decrypted_name]
    date_filter = ""
    if start_date and end_date:
        date_filter = "AND di.date BETWEEN %s AND %s"
        params.extend([start_date, end_date])

    query = f"""
        SELECT
            di.record_id, di.date, di.customer_id,
            c.name as customer_name,
            ae.grade_code, ae.category,
            ae.suggestion_text
        FROM daily_infos di
        JOIN customers c ON di.customer_id = c.customer_id
        LEFT JOIN ai_evaluations ae ON ae.record_id = di.record_id
        WHERE (
            di.record_id IN (
                SELECT dp.record_id FROM daily_physicals dp WHERE dp.writer_name = %s
                UNION
                SELECT dc.record_id FROM daily_cognitives dc WHERE dc.writer_name = %s
            )
        )
        {date_filter}
        ORDER BY di.date DESC
    """
    with db_query() as cursor:
        cursor.execute(query, params)
        records = cursor.fetchall()

    # 복호화 + 마스킹
    processed_records = []
    for r in records:
        row = dict(r)
        if row.get("customer_name"):
            plain = enc.safe_decrypt(row["customer_name"])
            row["customer_name"] = plain if admin else mask_name(plain)
        processed_records.append(row)

    display_name = decrypted_name if admin else mask_name(decrypted_name)
    return {
        "user_id": user["user_id"],
        "name": display_name,
        "records": processed_records,
    }


# ── 직원 평가(employee_evaluations) 기반 엔드포인트 ─────────────────


@router.get("/dashboard/emp-eval-trend")
def get_emp_eval_trend(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """직원 평가 유형별 일별 추이 (누락/내용부족/오타/문법/오류)"""
    from modules.db_connection import db_query

    params = []
    where = ""
    if start_date and end_date:
        where = "WHERE ee.evaluation_date BETWEEN %s AND %s"
        params = [start_date, end_date]

    query = f"""
        SELECT
            ee.evaluation_date as eval_date,
            SUM(CASE ee.evaluation_type WHEN '누락' THEN 1 ELSE 0 END) as cnt_누락,
            SUM(CASE ee.evaluation_type WHEN '내용부족' THEN 1 ELSE 0 END) as cnt_내용부족,
            SUM(CASE ee.evaluation_type WHEN '오타' THEN 1 ELSE 0 END) as cnt_오타,
            SUM(CASE ee.evaluation_type WHEN '문법' THEN 1 ELSE 0 END) as cnt_문법,
            SUM(CASE ee.evaluation_type WHEN '오류' THEN 1 ELSE 0 END) as cnt_오류
        FROM employee_evaluations ee
        {where}
        GROUP BY ee.evaluation_date
        ORDER BY ee.evaluation_date
    """
    with db_query() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()

    return [
        {
            "date": str(r["eval_date"]),
            "누락": r["cnt_누락"] or 0,
            "내용부족": r["cnt_내용부족"] or 0,
            "오타": r["cnt_오타"] or 0,
            "문법": r["cnt_문법"] or 0,
            "오류": r["cnt_오류"] or 0,
        }
        for r in rows
    ]


@router.get("/dashboard/emp-eval-category")
def get_emp_eval_category(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """직원 평가 카테고리별 건수"""
    from modules.db_connection import db_query

    params = []
    where = ""
    if start_date and end_date:
        where = "WHERE evaluation_date BETWEEN %s AND %s"
        params = [start_date, end_date]

    query = f"""
        SELECT category, COUNT(*) as count
        FROM employee_evaluations
        {where}
        GROUP BY category
        ORDER BY count DESC
    """
    with db_query() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()

    return [{"category": r["category"], "count": r["count"]} for r in rows]


@router.get("/dashboard/emp-eval-rankings")
def get_emp_eval_rankings(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """직원별 지적 건수 랭킹"""
    from modules.db_connection import db_query

    date_join = ""
    params: list = []
    if start_date and end_date:
        date_join = "AND ee.evaluation_date BETWEEN %s AND %s"
        params = [start_date, end_date]

    query = f"""
        SELECT
            u.user_id,
            u.name,
            COUNT(ee.emp_eval_id) as total_count,
            SUM(CASE ee.evaluation_type WHEN '누락' THEN 1 ELSE 0 END) as cnt_누락,
            SUM(CASE ee.evaluation_type WHEN '내용부족' THEN 1 ELSE 0 END) as cnt_내용부족,
            SUM(CASE ee.evaluation_type WHEN '오타' THEN 1 ELSE 0 END) as cnt_오타,
            SUM(CASE ee.evaluation_type WHEN '문법' THEN 1 ELSE 0 END) as cnt_문법,
            SUM(CASE ee.evaluation_type WHEN '오류' THEN 1 ELSE 0 END) as cnt_오류
        FROM users u
        LEFT JOIN employee_evaluations ee ON ee.target_user_id = u.user_id {date_join}
        WHERE u.work_status = '재직'
        GROUP BY u.user_id, u.name
        ORDER BY total_count DESC, u.name
    """
    with db_query() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()

    enc = EncryptionService()
    admin = is_admin(current_user)
    result = []
    for r in rows:
        types = {
            "누락": r["cnt_누락"] or 0,
            "내용부족": r["cnt_내용부족"] or 0,
            "오타": r["cnt_오타"] or 0,
            "문법": r["cnt_문법"] or 0,
            "오류": r["cnt_오류"] or 0,
        }
        main_type = max(types, key=lambda k: types[k]) if any(types.values()) else "-"
        plain = enc.safe_decrypt(r["name"])
        result.append({
            "user_id": r["user_id"],
            "name": plain if admin else mask_name(plain),
            "total_count": r["total_count"] or 0,
            "main_type": main_type,
        })
    return result


@router.get("/dashboard/employee/{user_id}/emp-eval-history")
def get_employee_eval_history(
    user_id: int,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """직원별 지적 이력 상세"""
    from modules.db_connection import db_query

    with db_query() as cursor:
        cursor.execute("SELECT user_id, name FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="직원을 찾을 수 없습니다.")

    enc = EncryptionService()
    admin = is_admin(current_user)
    decrypted_name = enc.safe_decrypt(user["name"])

    params: list = [user_id]
    date_filter = ""
    if start_date and end_date:
        date_filter = "AND ee.evaluation_date BETWEEN %s AND %s"
        params.extend([start_date, end_date])

    query = f"""
        SELECT
            ee.emp_eval_id,
            ee.evaluation_date,
            ee.target_date,
            ee.category,
            ee.evaluation_type,
            ee.comment,
            ee.score
        FROM employee_evaluations ee
        WHERE ee.target_user_id = %s
        {date_filter}
        ORDER BY ee.evaluation_date DESC, ee.emp_eval_id DESC
    """
    with db_query() as cursor:
        cursor.execute(query, params)
        records = cursor.fetchall()

    return {
        "user_id": user["user_id"],
        "name": decrypted_name if admin else mask_name(decrypted_name),
        "records": [
            {
                "emp_eval_id": r["emp_eval_id"],
                "evaluation_date": str(r["evaluation_date"]) if r["evaluation_date"] else None,
                "target_date": str(r["target_date"]) if r["target_date"] else None,
                "category": r["category"],
                "evaluation_type": r["evaluation_type"],
                "comment": r["comment"],
                "score": r["score"],
            }
            for r in records
        ],
    }


@router.get("/dashboard/period-comparison")
def get_period_comparison(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """선택 기간 vs 이전 기간 유형별 지적 건수 비교."""
    from modules.db_connection import db_query

    empty_period = {"start": None, "end": None, "total": 0, "by_type": {}}
    if not start_date or not end_date:
        return {
            "current_period": empty_period,
            "previous_period": empty_period,
            "change_rate": None,
        }

    period_length = (end_date - start_date).days
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_length)

    def _fetch_period(cursor, sd, ed):
        cursor.execute(
            "SELECT evaluation_type, COUNT(*) as cnt "
            "FROM employee_evaluations "
            "WHERE evaluation_date BETWEEN %s AND %s "
            "GROUP BY evaluation_type",
            (sd, ed),
        )
        rows = cursor.fetchall()
        by_type = {r["evaluation_type"]: r["cnt"] for r in rows}
        total = sum(by_type.values())
        return {"start": str(sd), "end": str(ed), "total": total, "by_type": by_type}

    with db_query() as cursor:
        current = _fetch_period(cursor, start_date, end_date)
        previous = _fetch_period(cursor, prev_start, prev_end)

    change_rate = None
    if previous["total"] > 0:
        change_rate = round((current["total"] - previous["total"]) / previous["total"] * 100, 2)

    return {
        "current_period": current,
        "previous_period": previous,
        "change_rate": change_rate,
    }


@router.get("/dashboard/kpi-summary")
def get_kpi_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """KPI 카드에 필요한 지표 + 이전 기간 대비 delta."""
    from modules.db_connection import db_query

    def _fetch_kpi(cursor, sd, ed):
        if sd and ed:
            cursor.execute(
                "SELECT COUNT(*) as total FROM employee_evaluations "
                "WHERE evaluation_date BETWEEN %s AND %s",
                (sd, ed),
            )
        else:
            cursor.execute("SELECT COUNT(*) as total FROM employee_evaluations")
        total = cursor.fetchone()["total"]

        if sd and ed:
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM ("
                "  SELECT target_user_id FROM employee_evaluations "
                "  WHERE evaluation_date BETWEEN %s AND %s "
                "  GROUP BY target_user_id HAVING COUNT(*) >= 5"
                ") sub",
                (sd, ed),
            )
        else:
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM ("
                "  SELECT target_user_id FROM employee_evaluations "
                "  GROUP BY target_user_id HAVING COUNT(*) >= 5"
                ") sub"
            )
        high_risk = cursor.fetchone()["cnt"]

        if sd and ed:
            cursor.execute(
                "SELECT COUNT(DISTINCT target_user_id) as emp_cnt "
                "FROM employee_evaluations "
                "WHERE evaluation_date BETWEEN %s AND %s",
                (sd, ed),
            )
        else:
            cursor.execute(
                "SELECT COUNT(DISTINCT target_user_id) as emp_cnt "
                "FROM employee_evaluations"
            )
        emp_cnt = cursor.fetchone()["emp_cnt"]
        avg = round(total / emp_cnt, 1) if emp_cnt > 0 else None

        return total, avg, high_risk

    with db_query() as cursor:
        cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE work_status = '재직'")
        total_employees = cursor.fetchone()["cnt"]

        curr_total, curr_avg, curr_high = _fetch_kpi(cursor, start_date, end_date)

        # 이전 기간 계산
        prev_total, prev_avg, prev_high = 0, None, 0
        if start_date and end_date:
            period_length = (end_date - start_date).days
            prev_end = start_date - timedelta(days=1)
            prev_start = prev_end - timedelta(days=period_length)
            prev_total, prev_avg, prev_high = _fetch_kpi(cursor, prev_start, prev_end)

    def _delta(curr, prev):
        if prev is None or prev == 0:
            return None
        return round((curr - prev) / prev * 100, 1)

    return {
        "total_issues": curr_total,
        "total_issues_prev": prev_total,
        "total_issues_delta": _delta(curr_total, prev_total),
        "avg_per_employee": curr_avg,
        "avg_per_employee_prev": prev_avg,
        "avg_per_employee_delta": _delta(curr_avg, prev_avg) if curr_avg is not None and prev_avg is not None else None,
        "high_risk_count": curr_high,
        "high_risk_count_prev": prev_high,
        "total_employees": total_employees,
    }


@router.get("/dashboard/employee/{user_id}/monthly-trend")
def get_employee_monthly_trend(
    user_id: int,
    months: int = Query(6, ge=1, le=24),
):
    """직원별 최근 N개월 월별 지적 건수."""
    from modules.db_connection import db_query

    with db_query() as cursor:
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="직원을 찾을 수 없습니다.")

        cursor.execute(
            "SELECT CONCAT(YEAR(evaluation_date), '-', LPAD(MONTH(evaluation_date), 2, '0')) as month, "
            "COUNT(*) as count "
            "FROM employee_evaluations "
            "WHERE target_user_id = %s AND evaluation_date >= DATE_SUB(CURDATE(), INTERVAL %s MONTH) "
            "GROUP BY month ORDER BY month",
            (user_id, months),
        )
        rows = cursor.fetchall()

    return [{"month": r["month"], "count": r["count"]} for r in rows]
