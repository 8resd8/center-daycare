from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date


class EmployeeBase(BaseModel):
    name: str
    gender: Optional[str] = None
    birth_date: Optional[str] = None   # 암호화/마스킹 후 문자열; date 객체도 자동 변환
    work_status: str = "재직"
    job_type: Optional[str] = None
    hire_date: Optional[date] = None
    resignation_date: Optional[date] = None
    license_name: Optional[str] = None
    license_date: Optional[date] = None

    @field_validator("birth_date", mode="before")
    @classmethod
    def coerce_birth_date(cls, v):
        if v is None:
            return None
        if isinstance(v, date):
            return v.isoformat()
        return str(v)

    model_config = {"populate_by_name": True}


class EmployeeCreate(EmployeeBase):
    username: str
    password: str


class EmployeeUpdate(EmployeeBase):
    pass


class EmployeeResponse(EmployeeBase):
    user_id: int

    model_config = {"from_attributes": True}
