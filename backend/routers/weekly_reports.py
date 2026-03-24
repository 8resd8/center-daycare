from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import date

from backend.dependencies import get_weekly_status_repo, get_report_service
from backend.schemas.weekly_reports import (
    WeeklyReportResponse,
    WeeklyReportGenerateRequest,
    WeeklyReportSaveRequest,
)
from modules.repositories.weekly_status import WeeklyStatusRepository
from modules.services.weekly_report_service import ReportService
from modules.weekly_data_analyzer import compute_weekly_status

router = APIRouter()


@router.get("/weekly-reports", response_model=List[WeeklyReportResponse])
def list_weekly_reports(
    customer_id: int = Query(...),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    repo: WeeklyStatusRepository = Depends(get_weekly_status_repo),
):
    if start_date and end_date:
        report_text = repo.load_weekly_status(customer_id, start_date, end_date)
        if report_text:
            return [WeeklyReportResponse(
                customer_id=customer_id,
                start_date=start_date,
                end_date=end_date,
                report_text=report_text,
            )]
        return []
    all_reports = repo.get_all_by_customer(customer_id)
    return [
        WeeklyReportResponse(
            customer_id=customer_id,
            start_date=r["start_date"],
            end_date=r["end_date"],
            report_text=r["report_text"],
        )
        for r in all_reports
    ]


@router.post("/weekly-reports/generate")
def generate_weekly_report(
    body: WeeklyReportGenerateRequest,
    report_service: ReportService = Depends(get_report_service),
    weekly_repo: WeeklyStatusRepository = Depends(get_weekly_status_repo),
):
    """AI 주간 보고서 생성"""
    from modules.repositories.customer import CustomerRepository
    customer_repo = CustomerRepository()
    customer = customer_repo.get_customer(body.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="수급자를 찾을 수 없습니다.")

    # 주간 데이터 분석 (compute_weekly_status: DB에서 직접 조회)
    analysis_payload = compute_weekly_status(
        customer_name=customer["name"],
        week_start_str=str(body.start_date),
        customer_id=body.customer_id,
        use_cache=False,
    )

    # 이전 주간 보고서 포함
    from datetime import timedelta
    prev_end = body.start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=6)
    prev_report = weekly_repo.load_weekly_status(body.customer_id, prev_start, prev_end)
    if analysis_payload and isinstance(analysis_payload, dict):
        analysis_payload["previous_weekly_report"] = prev_report or ""

    result = report_service.generate_weekly_report(
        customer_name=customer["name"],
        date_range=(body.start_date, body.end_date),
        analysis_payload=analysis_payload,
    )

    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return {"report_text": result}


@router.put("/weekly-reports/{customer_id}", status_code=200)
def save_weekly_report(
    customer_id: int,
    body: WeeklyReportSaveRequest,
    repo: WeeklyStatusRepository = Depends(get_weekly_status_repo),
):
    repo.save_weekly_status(
        customer_id=customer_id,
        start_date=body.start_date,
        end_date=body.end_date,
        report_text=body.report_text,
    )
    return {"message": "저장 완료"}
