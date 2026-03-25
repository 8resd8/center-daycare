from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List, Optional

from backend.dependencies import get_customer_repo, get_current_user
from backend.encryption import apply_customer_mask
from backend.schemas.customers import CustomerCreate, CustomerUpdate, CustomerResponse
from modules.repositories.customer import CustomerRepository
from modules.repositories.audit import AuditRepository

router = APIRouter(dependencies=[Depends(get_current_user)])


def _audit_repo() -> AuditRepository:
    return AuditRepository()


def _maybe_mask(data: dict, current_user: dict) -> dict:
    if current_user.get("role") != "ADMIN":
        return apply_customer_mask(data)
    return data


@router.get("/customers", response_model=List[CustomerResponse])
def list_customers(
    request: Request,
    keyword: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    repo: CustomerRepository = Depends(get_customer_repo),
    current_user: dict = Depends(get_current_user),
):
    rows = repo.list_customers(keyword=keyword)
    masked = [_maybe_mask(r, current_user) for r in rows]
    _audit_repo().log(
        user_id=current_user["user_id"],
        action="READ",
        resource="customer",
        ip=request.client.host if request.client else None,
    )
    return masked


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
def get_customer(
    request: Request,
    customer_id: int,
    repo: CustomerRepository = Depends(get_customer_repo),
    current_user: dict = Depends(get_current_user),
):
    customer = repo.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="수급자를 찾을 수 없습니다.")
    _audit_repo().log(
        user_id=current_user["user_id"],
        action="READ",
        resource="customer",
        res_id=customer_id,
        ip=request.client.host if request.client else None,
    )
    return _maybe_mask(customer, current_user)


@router.post("/customers", response_model=CustomerResponse, status_code=201)
def create_customer(
    request: Request,
    body: CustomerCreate,
    repo: CustomerRepository = Depends(get_customer_repo),
    current_user: dict = Depends(get_current_user),
):
    customer_id = repo.create_customer(
        name=body.name,
        birth_date=body.birth_date,
        gender=body.gender,
        recognition_no=body.recognition_no,
        benefit_start_date=body.benefit_start_date,
        grade=body.grade,
    )
    customer = repo.get_customer(customer_id)
    _audit_repo().log(
        user_id=current_user["user_id"],
        action="CREATE",
        resource="customer",
        res_id=customer_id,
        ip=request.client.host if request.client else None,
    )
    return _maybe_mask(customer, current_user)


@router.put("/customers/{customer_id}", response_model=CustomerResponse)
def update_customer(
    request: Request,
    customer_id: int,
    body: CustomerUpdate,
    repo: CustomerRepository = Depends(get_customer_repo),
    current_user: dict = Depends(get_current_user),
):
    repo.update_customer(
        customer_id=customer_id,
        name=body.name,
        birth_date=body.birth_date,
        gender=body.gender,
        recognition_no=body.recognition_no,
        benefit_start_date=body.benefit_start_date,
        grade=body.grade,
    )
    customer = repo.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="수급자를 찾을 수 없습니다.")
    _audit_repo().log(
        user_id=current_user["user_id"],
        action="UPDATE",
        resource="customer",
        res_id=customer_id,
        ip=request.client.host if request.client else None,
    )
    return _maybe_mask(customer, current_user)


@router.delete("/customers/{customer_id}", status_code=204)
def delete_customer(
    request: Request,
    customer_id: int,
    repo: CustomerRepository = Depends(get_customer_repo),
    current_user: dict = Depends(get_current_user),
):
    affected = repo.delete_customer(customer_id)
    if not affected:
        raise HTTPException(status_code=404, detail="수급자를 찾을 수 없습니다.")
    _audit_repo().log(
        user_id=current_user["user_id"],
        action="DELETE",
        resource="customer",
        res_id=customer_id,
        ip=request.client.host if request.client else None,
    )
