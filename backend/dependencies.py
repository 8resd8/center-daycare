"""공통 의존성 (Dependency Injection)"""

from modules.repositories.customer import CustomerRepository
from modules.repositories.daily_info import DailyInfoRepository
from modules.repositories.weekly_status import WeeklyStatusRepository
from modules.repositories.ai_evaluation import AiEvaluationRepository
from modules.repositories.employee_evaluation import EmployeeEvaluationRepository
from modules.repositories.user import UserRepository
from modules.services.daily_report_service import EvaluationService
from modules.services.weekly_report_service import ReportService


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
