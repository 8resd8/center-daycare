"""대시보드 라우터"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import date

router = APIRouter()


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
):
    """직원별 기록 및 평가 랭킹"""
    from modules.db_connection import db_query

    params = []
    date_filter = ""
    if start_date and end_date:
        date_filter = "AND di.date BETWEEN %s AND %s"
        params = [start_date, end_date]

    query = f"""
        SELECT
            u.user_id,
            u.name,
            COUNT(DISTINCT di.record_id) as total_records,
            SUM(CASE ae.grade_code WHEN '우수' THEN 1 ELSE 0 END) as excellent_count,
            SUM(CASE ae.grade_code WHEN '평균' THEN 1 ELSE 0 END) as average_count,
            SUM(CASE ae.grade_code WHEN '개선' THEN 1 ELSE 0 END) as improvement_count
        FROM users u
        LEFT JOIN daily_infos di ON (
            di.record_id IN (
                SELECT dp.record_id FROM daily_physicals dp WHERE dp.writer_name = u.name
                UNION
                SELECT dc.record_id FROM daily_cognitives dc WHERE dc.writer_name = u.name
            )
            {date_filter}
        )
        LEFT JOIN ai_evaluations ae ON ae.record_id = di.record_id
        WHERE u.work_status = '재직'
        GROUP BY u.user_id, u.name
        ORDER BY excellent_count DESC, total_records DESC
    """
    with db_query() as cursor:
        cursor.execute(query, params if params else [])
        rows = cursor.fetchall()

    result = []
    for r in rows:
        total = (r["excellent_count"] or 0) + (r["average_count"] or 0) + (r["improvement_count"] or 0)
        score = (
            ((r["excellent_count"] or 0) * 3 + (r["average_count"] or 0) * 2 + (r["improvement_count"] or 0)) / total
            if total > 0
            else 0.0
        )
        result.append({
            "user_id": r["user_id"],
            "name": r["name"],
            "total_records": r["total_records"] or 0,
            "excellent_count": r["excellent_count"] or 0,
            "average_count": r["average_count"] or 0,
            "improvement_count": r["improvement_count"] or 0,
            "score": round(score, 2),
        })

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
):
    """직원별 상세 기록 및 평가"""
    from modules.db_connection import db_query

    with db_query() as cursor:
        cursor.execute("SELECT user_id, name FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="직원을 찾을 수 없습니다.")

    params = [user["name"], user["name"]]
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

    return {
        "user_id": user["user_id"],
        "name": user["name"],
        "records": [dict(r) for r in records],
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
        result.append({
            "user_id": r["user_id"],
            "name": r["name"],
            "total_count": r["total_count"] or 0,
            "main_type": main_type,
        })
    return result


@router.get("/dashboard/employee/{user_id}/emp-eval-history")
def get_employee_eval_history(
    user_id: int,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """직원별 지적 이력 상세"""
    from modules.db_connection import db_query

    with db_query() as cursor:
        cursor.execute("SELECT user_id, name FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="직원을 찾을 수 없습니다.")

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
        "name": user["name"],
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
