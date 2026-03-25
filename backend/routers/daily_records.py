from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import date

from backend.dependencies import get_daily_info_repo, get_current_user
from backend.schemas.daily_records import DailyRecordSummary, CustomerWithRecords
from modules.repositories.daily_info import DailyInfoRepository

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/daily-records", response_model=List[DailyRecordSummary])
def list_daily_records(
    customer_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    repo: DailyInfoRepository = Depends(get_daily_info_repo),
):
    if customer_id is None:
        raise HTTPException(status_code=400, detail="customer_id는 필수입니다.")
    return repo.get_customer_records(
        customer_id=customer_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/daily-records/customers-with-records", response_model=List[CustomerWithRecords])
def get_customers_with_records(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    repo: DailyInfoRepository = Depends(get_daily_info_repo),
):
    return repo.get_customers_with_records(start_date=start_date, end_date=end_date)


@router.get("/daily-records/{record_id}", response_model=DailyRecordSummary)
def get_daily_record(
    record_id: int,
    repo: DailyInfoRepository = Depends(get_daily_info_repo),
):
    """특정 record_id의 기록 조회"""
    from modules.db_connection import db_query
    query = """
        SELECT
            di.record_id, di.customer_id, di.date, di.total_service_time,
            dp.note AS physical_note, dp.writer_name AS writer_physical,
            dp.meal_breakfast, dp.meal_lunch, dp.meal_dinner,
            dp.toilet_care, dp.bath_time,
            dn.bp_temp,
            dr.prog_therapy,
            dc.note AS cognitive_note, dc.writer_name AS writer_cognitive,
            dn.note AS nursing_note, dn.writer_name AS writer_nursing,
            dr.note AS functional_note, dr.writer_name AS writer_recovery
        FROM daily_infos di
        LEFT JOIN daily_physicals dp ON dp.record_id = di.record_id
        LEFT JOIN daily_cognitives dc ON dc.record_id = di.record_id
        LEFT JOIN daily_nursings dn ON dn.record_id = di.record_id
        LEFT JOIN daily_recoveries dr ON dr.record_id = di.record_id
        WHERE di.record_id = %s
    """
    with db_query() as cursor:
        cursor.execute(query, (record_id,))
        result = cursor.fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="기록을 찾을 수 없습니다.")
    return result


@router.delete("/daily-records/{record_id}", status_code=204)
def delete_daily_record(
    record_id: int,
    repo: DailyInfoRepository = Depends(get_daily_info_repo),
):
    repo.delete_daily_record(record_id)
