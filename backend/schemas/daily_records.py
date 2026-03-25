from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import date


def _parse_date(v):
    if v is None or isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            parts = v.split('-')
            if len(parts) == 3:
                return date(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, AttributeError):
            pass
    return v


class DailyRecordSummary(BaseModel):
    record_id: int
    customer_id: int
    date: date
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    total_service_time: Optional[str] = None
    transport_service: Optional[str] = None
    transport_vehicles: Optional[str] = None
    # 신체활동
    hygiene_care: Optional[str] = None
    bath_time: Optional[str] = None
    bath_method: Optional[str] = None
    meal_breakfast: Optional[str] = None
    meal_lunch: Optional[str] = None
    meal_dinner: Optional[str] = None
    toilet_care: Optional[str] = None
    mobility_care: Optional[str] = None
    physical_note: Optional[str] = None
    writer_phy: Optional[str] = None
    # 인지관리
    cog_support: Optional[str] = None
    comm_support: Optional[str] = None
    cognitive_note: Optional[str] = None
    writer_cog: Optional[str] = None
    # 간호관리
    bp_temp: Optional[str] = None
    health_manage: Optional[str] = None
    nursing_manage: Optional[str] = None
    emergency: Optional[str] = None
    nursing_note: Optional[str] = None
    writer_nur: Optional[str] = None
    # 기능회복
    prog_basic: Optional[str] = None
    prog_activity: Optional[str] = None
    prog_cognitive: Optional[str] = None
    prog_therapy: Optional[str] = None
    prog_enhance_detail: Optional[str] = None
    functional_note: Optional[str] = None
    writer_func: Optional[str] = None

    model_config = {"from_attributes": True}

    @field_validator('date', mode='before')
    @classmethod
    def parse_date_fields(cls, v):
        return _parse_date(v)


class CustomerWithRecords(BaseModel):
    customer_id: int
    name: str
    birth_date: Optional[str] = None   # 암호화/마스킹 후 문자열
    grade: Optional[str] = None
    recognition_no: Optional[str] = None
    record_count: int = 0
    first_date: Optional[date] = None
    last_date: Optional[date] = None

    @field_validator('birth_date', mode='before')
    @classmethod
    def coerce_birth_date(cls, v):
        if v is None:
            return None
        if isinstance(v, date):
            return v.isoformat()
        return str(v)

    @field_validator('first_date', 'last_date', mode='before')
    @classmethod
    def parse_date_fields(cls, v):
        return _parse_date(v)
