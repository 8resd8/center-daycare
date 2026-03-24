from pydantic import BaseModel
from typing import Optional, Dict, Any, Tuple
from datetime import date


class WeeklyReportResponse(BaseModel):
    customer_id: int
    start_date: date
    end_date: date
    report_text: str


class WeeklyReportGenerateRequest(BaseModel):
    customer_id: int
    start_date: date
    end_date: date


class WeeklyReportSaveRequest(BaseModel):
    customer_id: int
    start_date: date
    end_date: date
    report_text: str
