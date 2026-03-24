from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import date


class DashboardSummary(BaseModel):
    total_customers: int
    total_records: int
    total_employees: int
    avg_grade_score: Optional[float] = None


class EvaluationTrendItem(BaseModel):
    date: str
    excellent: int = 0
    average: int = 0
    improvement: int = 0


class EmployeeRankingItem(BaseModel):
    user_id: int
    name: str
    total_records: int
    excellent_count: int
    average_count: int
    improvement_count: int
    score: float


class AiGradeDistItem(BaseModel):
    grade: str
    count: int


class EmployeeDetailItem(BaseModel):
    user_id: int
    name: str
    records: List[Dict[str, Any]] = []
    evaluations: List[Dict[str, Any]] = []
