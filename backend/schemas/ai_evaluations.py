from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AiEvaluationResponse(BaseModel):
    ai_eval_id: Optional[int] = None
    record_id: int
    category: str
    oer_fidelity: Optional[str] = None
    specificity_score: Optional[str] = None
    grammar_score: Optional[str] = None
    grade_code: Optional[str] = None
    reason_text: Optional[str] = None
    suggestion_text: Optional[str] = None
    original_text: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AiEvaluateRequest(BaseModel):
    record_id: int
    category: str
    note_text: str
    writer_user_id: int = 0
