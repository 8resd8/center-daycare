from pydantic import BaseModel, field_validator
from typing import Optional
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


class CustomerBase(BaseModel):
    name: str
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    recognition_no: Optional[str] = None
    benefit_start_date: Optional[date] = None
    grade: Optional[str] = None

    @field_validator('birth_date', 'benefit_start_date', mode='before')
    @classmethod
    def parse_date_fields(cls, v):
        return _parse_date(v)


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(CustomerBase):
    pass


class CustomerResponse(CustomerBase):
    customer_id: int

    model_config = {"from_attributes": True}
