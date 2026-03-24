from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class EmployeeEvaluationBase(BaseModel):
    record_id: Optional[int] = None
    target_user_id: int
    category: str
    evaluation_type: str
    evaluation_date: date
    target_date: Optional[date] = None
    evaluator_user_id: Optional[int] = None
    score: int = 1
    comment: Optional[str] = None


class EmployeeEvaluationCreate(EmployeeEvaluationBase):
    pass


class EmployeeEvaluationUpdate(BaseModel):
    category: Optional[str] = None
    evaluation_type: Optional[str] = None
    evaluation_date: date
    target_date: Optional[date] = None
    evaluator_user_id: Optional[int] = None
    score: int = 1
    comment: Optional[str] = None


class EmployeeEvaluationResponse(EmployeeEvaluationBase):
    emp_eval_id: int
    target_user_name: Optional[str] = None
    evaluator_user_name: Optional[str] = None

    model_config = {"from_attributes": True}


class UserDropdownItem(BaseModel):
    user_id: int
    name: str
