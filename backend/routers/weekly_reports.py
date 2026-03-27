from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import date

from backend.dependencies import get_weekly_status_repo, get_report_service, get_current_user, require_admin
from backend.schemas.weekly_reports import (
    WeeklyReportResponse,
    WeeklyReportGenerateRequest,
    WeeklyReportGenerateResponse,
    WeeklyAnalysisResponse,
    WeeklyReportSaveRequest,
)
from modules.repositories.weekly_status import WeeklyStatusRepository
from modules.services.weekly_report_service import ReportService
from modules.weekly_data_analyzer import compute_weekly_status

router = APIRouter(dependencies=[Depends(get_current_user)])


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


@router.get("/weekly-reports/analysis", response_model=WeeklyAnalysisResponse)
def get_weekly_analysis(
    customer_id: int = Query(...),
    start_date: date = Query(...),
    end_date: date = Query(...),
):
    """전주/이번주 변화량 분석 데이터 조회 (AI 생성 없이 빠르게 반환)"""
    from modules.repositories.customer import CustomerRepository
    customer_repo = CustomerRepository()
    customer = customer_repo.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="수급자를 찾을 수 없습니다.")

    analysis_result = compute_weekly_status(
        customer_name=customer["name"],
        week_start_str=str(start_date),
        customer_id=customer_id,
        use_cache=False,
    )

    if not isinstance(analysis_result, dict):
        return WeeklyAnalysisResponse()

    trend = analysis_result.get("trend", {})
    weekly_table = trend.get("weekly_table", []) if isinstance(trend, dict) else []
    scores = analysis_result.get("scores", {})

    prev_range = None
    curr_range = None
    ranges = analysis_result.get("ranges")
    if ranges:
        prev_r, curr_r = ranges
        prev_range = [str(prev_r[0]), str(prev_r[1])]
        curr_range = [str(curr_r[0]), str(curr_r[1])]

    prev_prog_entries = trend.get("prev_prog_entries", []) if isinstance(trend, dict) else []
    curr_prog_entries = trend.get("curr_prog_entries", []) if isinstance(trend, dict) else []

    return WeeklyAnalysisResponse(
        weekly_table=weekly_table,
        scores=scores,
        prev_range=prev_range,
        curr_range=curr_range,
        prev_prog_entries=prev_prog_entries,
        curr_prog_entries=curr_prog_entries,
    )


@router.post("/weekly-reports/generate", response_model=WeeklyReportGenerateResponse)
def generate_weekly_report(
    body: WeeklyReportGenerateRequest,
    report_service: ReportService = Depends(get_report_service),
    weekly_repo: WeeklyStatusRepository = Depends(get_weekly_status_repo),
    _: dict = Depends(require_admin),
):
    """AI 주간 보고서 생성"""
    from modules.repositories.customer import CustomerRepository
    customer_repo = CustomerRepository()
    customer = customer_repo.get_customer(body.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="수급자를 찾을 수 없습니다.")

    # 주간 데이터 분석 (compute_weekly_status: DB에서 직접 조회)
    analysis_result = compute_weekly_status(
        customer_name=customer["name"],
        week_start_str=str(body.start_date),
        customer_id=body.customer_id,
        use_cache=False,
    )

    # trend.ai_payload 추출 (서비스가 기대하는 구조)
    trend = analysis_result.get("trend", {}) if isinstance(analysis_result, dict) else {}
    ai_payload = trend.get("ai_payload", {}) if isinstance(trend, dict) else {}

    # 이전 주간 보고서 포함
    from datetime import timedelta
    prev_end = body.start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=6)
    prev_report = weekly_repo.load_weekly_status(body.customer_id, prev_start, prev_end)
    ai_payload["previous_weekly_report"] = prev_report or ""

    result = report_service.generate_weekly_report(
        customer_name=customer["name"],
        date_range=(body.start_date, body.end_date),
        analysis_payload=ai_payload,
    )

    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    # 전주/이번주 변화량 데이터 포함
    weekly_table = trend.get("weekly_table", []) if isinstance(trend, dict) else []
    scores = analysis_result.get("scores", {}) if isinstance(analysis_result, dict) else {}

    return WeeklyReportGenerateResponse(
        report_text=result,
        weekly_table=weekly_table,
        scores=scores,
    )


@router.put("/weekly-reports/{customer_id}", status_code=200)
def save_weekly_report(
    customer_id: int,
    body: WeeklyReportSaveRequest,
    repo: WeeklyStatusRepository = Depends(get_weekly_status_repo),
    _: dict = Depends(require_admin),
):
    repo.save_weekly_status(
        customer_id=customer_id,
        start_date=body.start_date,
        end_date=body.end_date,
        report_text=body.report_text,
    )
    return {"message": "저장 완료"}
