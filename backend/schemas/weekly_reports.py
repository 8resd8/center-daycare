from pydantic import BaseModel
from typing import Optional, Dict, Any, List
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


class WeeklyReportGenerateResponse(BaseModel):
    report_text: str
    weekly_table: List[Dict[str, Any]] = []
    scores: Dict[str, Any] = {}


class WeeklyAnalysisResponse(BaseModel):
    weekly_table: List[Dict[str, Any]] = []
    scores: Dict[str, Any] = {}
    prev_range: Optional[List[str]] = None   # ["YYYY-MM-DD", "YYYY-MM-DD"]
    curr_range: Optional[List[str]] = None
    prev_prog_entries: List[Dict[str, str]] = []   # [{date, detail}, ...]
    curr_prog_entries: List[Dict[str, str]] = []


class WeeklyReportSaveRequest(BaseModel):
    customer_id: int
    start_date: date
    end_date: date
    report_text: str
