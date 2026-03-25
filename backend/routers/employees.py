from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List, Optional

from passlib.context import CryptContext

from backend.dependencies import get_user_repo, get_current_user
from backend.encryption import apply_employee_mask, is_admin
from backend.schemas.employees import EmployeeCreate, EmployeeUpdate, EmployeeResponse
from modules.repositories.user import UserRepository
from modules.repositories.audit import AuditRepository

router = APIRouter(dependencies=[Depends(get_current_user)])
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _audit_repo() -> AuditRepository:
    return AuditRepository()


def _maybe_mask(data: dict, current_user: dict) -> dict:
    if not is_admin(current_user):
        return apply_employee_mask(data)
    return data


@router.get("/employees", response_model=List[EmployeeResponse])
def list_employees(
    request: Request,
    keyword: Optional[str] = Query(None),
    work_status: Optional[str] = Query(None),
    repo: UserRepository = Depends(get_user_repo),
    current_user: dict = Depends(get_current_user),
):
    rows = repo.list_users(keyword=keyword, work_status=work_status)
    masked = [_maybe_mask(r, current_user) for r in rows]
    _audit_repo().log(
        user_id=current_user["user_id"],
        action="READ",
        resource="employee",
        ip=request.client.host if request.client else None,
    )
    return masked


@router.get("/employees/{user_id}", response_model=EmployeeResponse)
def get_employee(
    request: Request,
    user_id: int,
    repo: UserRepository = Depends(get_user_repo),
    current_user: dict = Depends(get_current_user),
):
    employee = repo.get_user(user_id)
    if not employee:
        raise HTTPException(status_code=404, detail="직원을 찾을 수 없습니다.")
    _audit_repo().log(
        user_id=current_user["user_id"],
        action="READ",
        resource="employee",
        res_id=user_id,
        ip=request.client.host if request.client else None,
    )
    return _maybe_mask(employee, current_user)


@router.post("/employees", response_model=EmployeeResponse, status_code=201)
def create_employee(
    request: Request,
    body: EmployeeCreate,
    repo: UserRepository = Depends(get_user_repo),
    current_user: dict = Depends(get_current_user),
):
    hashed_password = _pwd_context.hash(body.password)
    user_id = repo.create_user(
        username=body.username,
        password=hashed_password,
        name=body.name,
        gender=body.gender,
        birth_date=body.birth_date,
        work_status=body.work_status,
        job_type=body.job_type,
        hire_date=body.hire_date,
        resignation_date=body.resignation_date,
        license_name=body.license_name,
        license_date=body.license_date,
    )
    employee = repo.get_user(user_id)
    _audit_repo().log(
        user_id=current_user["user_id"],
        action="CREATE",
        resource="employee",
        res_id=user_id,
        ip=request.client.host if request.client else None,
    )
    return _maybe_mask(employee, current_user)


@router.put("/employees/{user_id}", response_model=EmployeeResponse)
def update_employee(
    request: Request,
    user_id: int,
    body: EmployeeUpdate,
    repo: UserRepository = Depends(get_user_repo),
    current_user: dict = Depends(get_current_user),
):
    repo.update_user(
        user_id=user_id,
        name=body.name,
        gender=body.gender,
        birth_date=body.birth_date,
        work_status=body.work_status,
        job_type=body.job_type,
        hire_date=body.hire_date,
        resignation_date=body.resignation_date,
        license_name=body.license_name,
        license_date=body.license_date,
    )
    employee = repo.get_user(user_id)
    if not employee:
        raise HTTPException(status_code=404, detail="직원을 찾을 수 없습니다.")
    _audit_repo().log(
        user_id=current_user["user_id"],
        action="UPDATE",
        resource="employee",
        res_id=user_id,
        ip=request.client.host if request.client else None,
    )
    return _maybe_mask(employee, current_user)


@router.delete("/employees/{user_id}", status_code=204)
def soft_delete_employee(
    request: Request,
    user_id: int,
    repo: UserRepository = Depends(get_user_repo),
    current_user: dict = Depends(get_current_user),
):
    """퇴사 처리 (soft delete)"""
    affected = repo.soft_delete_user(user_id)
    if not affected:
        raise HTTPException(status_code=404, detail="직원을 찾을 수 없습니다.")
    _audit_repo().log(
        user_id=current_user["user_id"],
        action="DELETE",
        resource="employee",
        res_id=user_id,
        ip=request.client.host if request.client else None,
    )
