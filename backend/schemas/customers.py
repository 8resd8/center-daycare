from pydantic import BaseModel, field_validator
from typing import Optional, Union
from datetime import date


class CustomerBase(BaseModel):
    name: str
    birth_date: Optional[str] = None   # 암호화/마스킹 후 문자열; date 객체도 자동 변환
    gender: Optional[str] = None
    recognition_no: Optional[str] = None
    benefit_start_date: Optional[date] = None
    grade: Optional[str] = None

    @field_validator("birth_date", mode="before")
    @classmethod
    def coerce_birth_date(cls, v):
        if v is None:
            return None
        if isinstance(v, date):
            return v.isoformat()
        return str(v)

    model_config = {"populate_by_name": True}


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(CustomerBase):
    pass


class CustomerResponse(CustomerBase):
    customer_id: int

    model_config = {"from_attributes": True}
