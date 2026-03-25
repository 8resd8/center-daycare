"""공통 의존성 (Dependency Injection)"""

import os
from typing import Optional

from fastapi import Cookie, HTTPException
from jose import jwt, JWTError

from modules.repositories.customer import CustomerRepository
from modules.repositories.daily_info import DailyInfoRepository
from modules.repositories.weekly_status import WeeklyStatusRepository
from modules.repositories.ai_evaluation import AiEvaluationRepository
from modules.repositories.employee_evaluation import EmployeeEvaluationRepository
from modules.repositories.user import UserRepository
from modules.services.daily_report_service import EvaluationService
from modules.services.weekly_report_service import ReportService

_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production-use-random-32bytes")
_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


def get_customer_repo() -> CustomerRepository:
    return CustomerRepository()


def get_daily_info_repo() -> DailyInfoRepository:
    return DailyInfoRepository()


def get_weekly_status_repo() -> WeeklyStatusRepository:
    return WeeklyStatusRepository()


def get_ai_evaluation_repo() -> AiEvaluationRepository:
    return AiEvaluationRepository()


def get_employee_evaluation_repo() -> EmployeeEvaluationRepository:
    return EmployeeEvaluationRepository()


def get_user_repo() -> UserRepository:
    return UserRepository()


def get_evaluation_service() -> EvaluationService:
    return EvaluationService()


def get_report_service() -> ReportService:
    return ReportService()


def get_current_user(access_token: Optional[str] = Cookie(None)) -> dict:
    """httpOnly 쿠키에서 JWT 추출 및 검증."""
    if not access_token:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    try:
        payload = jwt.decode(access_token, _SECRET_KEY, algorithms=[_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
