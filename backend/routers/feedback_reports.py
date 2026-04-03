"""직원 피드백 리포트 라우터"""

import calendar
from fastapi import APIRouter, Depends, HTTPException

from backend.dependencies import require_admin, get_feedback_service
from backend.encryption import EncryptionService
from backend.schemas.feedback_reports import (
    FeedbackReportCreate,
    FeedbackReportResponse,
    FeedbackReportMonthItem,
)
from modules.db_connection import db_query
from modules.services.feedback_service import FeedbackService

router = APIRouter(dependencies=[Depends(require_admin)])


@router.post(
    "/dashboard/employee/{user_id}/feedback-report",
    response_model=FeedbackReportResponse,
)
def create_feedback_report(
    user_id: int,
    body: FeedbackReportCreate,
    service: FeedbackService = Depends(get_feedback_service),
):
    """AI 피드백 생성 & 저장 (ADMIN 전용)"""
    with db_query() as cursor:
        cursor.execute("SELECT user_id, name FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="직원을 찾을 수 없습니다.")

    enc = EncryptionService()
    employee_name = enc.safe_decrypt(user["name"])

    try:
        year, month = body.target_month.split("-")
        first_day = f"{year}-{month}-01"
        last_day_num = calendar.monthrange(int(year), int(month))[1]
        last_day = f"{year}-{month}-{last_day_num:02d}"
    except (ValueError, IndexError):
        raise HTTPException(
            status_code=422, detail="target_month는 'YYYY-MM' 형식이어야 합니다."
        )

    with db_query() as cursor:
        cursor.execute(
            "SELECT evaluation_date, target_date, category, evaluation_type, comment "
            "FROM employee_evaluations "
            "WHERE target_user_id = %s AND evaluation_date BETWEEN %s AND %s "
            "ORDER BY evaluation_date",
            (user_id, first_day, last_day),
        )
        evaluations = cursor.fetchall()

    try:
        result = service.generate_and_save(
            user_id=user_id,
            employee_name=employee_name,
            target_month=body.target_month,
            admin_note=body.admin_note,
            evaluations=[dict(r) for r in evaluations],
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return result


@router.get(
    "/dashboard/employee/{user_id}/feedback-reports",
    response_model=list[FeedbackReportMonthItem],
)
def list_feedback_months(
    user_id: int,
    service: FeedbackService = Depends(get_feedback_service),
):
    """저장된 월 목록 조회 (ADMIN 전용)"""
    with db_query() as cursor:
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="직원을 찾을 수 없습니다.")
    return service.list_months(user_id)


@router.get(
    "/dashboard/employee/{user_id}/feedback-report/{month}",
    response_model=FeedbackReportResponse,
)
def get_feedback_report(
    user_id: int,
    month: str,
    service: FeedbackService = Depends(get_feedback_service),
):
    """특정 월 피드백 리포트 조회 (ADMIN 전용)"""
    result = service.get_by_month(user_id, month)
    if not result:
        raise HTTPException(status_code=404, detail="해당 월 피드백 리포트가 없습니다.")
    return result
