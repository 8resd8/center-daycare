from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from backend.dependencies import get_employee_evaluation_repo
from backend.schemas.employee_evaluations import (
    EmployeeEvaluationCreate,
    EmployeeEvaluationUpdate,
    EmployeeEvaluationResponse,
    UserDropdownItem,
)
from modules.repositories.employee_evaluation import EmployeeEvaluationRepository

router = APIRouter()


@router.get("/employee-evaluations/users", response_model=List[UserDropdownItem])
def get_users_dropdown(
    repo: EmployeeEvaluationRepository = Depends(get_employee_evaluation_repo),
):
    """직원 목록 (드롭다운용)"""
    return repo.get_all_users()


@router.get("/employee-evaluations", response_model=List[EmployeeEvaluationResponse])
def get_employee_evaluations(
    record_id: int = Query(...),
    repo: EmployeeEvaluationRepository = Depends(get_employee_evaluation_repo),
):
    return repo.get_evaluations_by_record(record_id)


@router.post("/employee-evaluations", response_model=EmployeeEvaluationResponse, status_code=201)
def create_employee_evaluation(
    body: EmployeeEvaluationCreate,
    repo: EmployeeEvaluationRepository = Depends(get_employee_evaluation_repo),
):
    # 기존 평가 확인
    if body.record_id:
        existing_id = repo.find_existing_evaluation(
            record_id=body.record_id,
            target_user_id=body.target_user_id,
            category=body.category,
            evaluation_type=body.evaluation_type,
        )
        if existing_id:
            repo.update_evaluation(
                emp_eval_id=existing_id,
                evaluation_date=body.evaluation_date,
                category=body.category,
                evaluation_type=body.evaluation_type,
                target_date=body.target_date,
                evaluator_user_id=body.evaluator_user_id,
                score=body.score,
                comment=body.comment,
            )
            return repo.get_evaluations_by_record(body.record_id)[0]

    emp_eval_id = repo.save_evaluation(
        record_id=body.record_id,
        target_user_id=body.target_user_id,
        category=body.category,
        evaluation_type=body.evaluation_type,
        evaluation_date=body.evaluation_date,
        target_date=body.target_date,
        evaluator_user_id=body.evaluator_user_id,
        score=body.score,
        comment=body.comment,
    )

    if body.record_id:
        evals = repo.get_evaluations_by_record(body.record_id)
        for e in evals:
            if e["emp_eval_id"] == emp_eval_id:
                return e

    raise HTTPException(status_code=500, detail="평가 저장 실패")


@router.put("/employee-evaluations/{emp_eval_id}", status_code=200)
def update_employee_evaluation(
    emp_eval_id: int,
    body: EmployeeEvaluationUpdate,
    repo: EmployeeEvaluationRepository = Depends(get_employee_evaluation_repo),
):
    affected = repo.update_evaluation(
        emp_eval_id=emp_eval_id,
        evaluation_date=body.evaluation_date,
        category=body.category,
        evaluation_type=body.evaluation_type,
        target_date=body.target_date,
        evaluator_user_id=body.evaluator_user_id,
        score=body.score,
        comment=body.comment,
    )
    if not affected:
        raise HTTPException(status_code=404, detail="평가를 찾을 수 없습니다.")
    return {"message": "업데이트 완료"}


@router.delete("/employee-evaluations/{emp_eval_id}", status_code=204)
def delete_employee_evaluation(
    emp_eval_id: int,
    repo: EmployeeEvaluationRepository = Depends(get_employee_evaluation_repo),
):
    affected = repo.delete_evaluation(emp_eval_id)
    if not affected:
        raise HTTPException(status_code=404, detail="평가를 찾을 수 없습니다.")
