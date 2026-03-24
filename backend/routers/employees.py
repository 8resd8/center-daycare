from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from backend.dependencies import get_user_repo
from backend.schemas.employees import EmployeeCreate, EmployeeUpdate, EmployeeResponse
from modules.repositories.user import UserRepository

router = APIRouter()


@router.get("/employees", response_model=List[EmployeeResponse])
def list_employees(
    keyword: Optional[str] = Query(None),
    work_status: Optional[str] = Query(None),
    repo: UserRepository = Depends(get_user_repo),
):
    return repo.list_users(keyword=keyword, work_status=work_status)


@router.get("/employees/{user_id}", response_model=EmployeeResponse)
def get_employee(
    user_id: int,
    repo: UserRepository = Depends(get_user_repo),
):
    employee = repo.get_user(user_id)
    if not employee:
        raise HTTPException(status_code=404, detail="직원을 찾을 수 없습니다.")
    return employee


@router.post("/employees", response_model=EmployeeResponse, status_code=201)
def create_employee(
    body: EmployeeCreate,
    repo: UserRepository = Depends(get_user_repo),
):
    import hashlib
    hashed_password = hashlib.sha256(body.password.encode()).hexdigest()

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
    return employee


@router.put("/employees/{user_id}", response_model=EmployeeResponse)
def update_employee(
    user_id: int,
    body: EmployeeUpdate,
    repo: UserRepository = Depends(get_user_repo),
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
    return employee


@router.delete("/employees/{user_id}", status_code=204)
def soft_delete_employee(
    user_id: int,
    repo: UserRepository = Depends(get_user_repo),
):
    """퇴사 처리 (soft delete)"""
    affected = repo.soft_delete_user(user_id)
    if not affected:
        raise HTTPException(status_code=404, detail="직원을 찾을 수 없습니다.")
