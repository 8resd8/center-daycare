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


class EmployeeBase(BaseModel):
    name: str
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    work_status: str = "재직"
    job_type: Optional[str] = None
    hire_date: Optional[date] = None
    resignation_date: Optional[date] = None
    license_name: Optional[str] = None
    license_date: Optional[date] = None

    @field_validator('birth_date', 'hire_date', 'resignation_date', 'license_date', mode='before')
    @classmethod
    def parse_date_fields(cls, v):
        return _parse_date(v)


class EmployeeCreate(EmployeeBase):
    username: str
    password: str


class EmployeeUpdate(EmployeeBase):
    pass


class EmployeeResponse(EmployeeBase):
    user_id: int

    model_config = {"from_attributes": True}
