from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from backend.dependencies import get_ai_evaluation_repo, get_evaluation_service
from backend.schemas.ai_evaluations import AiEvaluationResponse, AiEvaluateRequest
from modules.repositories.ai_evaluation import AiEvaluationRepository
from modules.services.daily_report_service import EvaluationService

router = APIRouter()


@router.get("/ai-evaluations", response_model=List[AiEvaluationResponse])
def get_ai_evaluations(
    record_id: int = Query(...),
    repo: AiEvaluationRepository = Depends(get_ai_evaluation_repo),
):
    return repo.get_all_evaluations_by_record(record_id)


@router.post("/ai-evaluations/evaluate")
def evaluate_record(
    body: AiEvaluateRequest,
    service: EvaluationService = Depends(get_evaluation_service),
):
    """특이사항 AI 평가 실행"""
    result = service.process_daily_note_evaluation(
        record_id=body.record_id,
        category=body.category,
        note_text=body.note_text,
        note_writer_user_id=body.writer_user_id,
    )
    return result


@router.post("/ai-evaluations/evaluate-record/{record_id}")
def evaluate_full_record(
    record_id: int,
    service: EvaluationService = Depends(get_evaluation_service),
):
    """특정 record의 신체/인지 특이사항 전체 AI 평가"""
    from modules.db_connection import db_query
    query = """
        SELECT di.*, c.name as customer_name,
               dp.note as physical_note, dc.note as cognitive_note,
               dn.note as nursing_note, dr.note as functional_note
        FROM daily_infos di
        LEFT JOIN customers c ON di.customer_id = c.customer_id
        LEFT JOIN daily_physicals dp ON dp.record_id = di.record_id
        LEFT JOIN daily_cognitives dc ON dc.record_id = di.record_id
        LEFT JOIN daily_nursings dn ON dn.record_id = di.record_id
        LEFT JOIN daily_recoveries dr ON dr.record_id = di.record_id
        WHERE di.record_id = %s
    """
    with db_query() as cursor:
        cursor.execute(query, (record_id,))
        record = cursor.fetchone()

    if not record:
        raise HTTPException(status_code=404, detail="기록을 찾을 수 없습니다.")

    ai_result = service.evaluate_special_note_with_ai(record)
    if not ai_result:
        raise HTTPException(status_code=500, detail="AI 평가에 실패했습니다.")

    # DB 저장
    service.save_special_note_evaluation(record_id, ai_result)

    return ai_result
