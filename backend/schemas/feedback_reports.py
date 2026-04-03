"""직원 피드백 리포트 스키마"""

from pydantic import BaseModel
from typing import Optional, Any


class FeedbackReportCreate(BaseModel):
    target_month: str
    admin_note: Optional[str] = None


class FeedbackReportMonthItem(BaseModel):
    report_id: int
    target_month: str
    created_at: str


class FeedbackReportResponse(BaseModel):
    report_id: int
    user_id: int
    target_month: str
    admin_note: Optional[str]
    ai_result: Any
    created_at: str
    updated_at: str
