from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from backend.dependencies import get_customer_repo
from backend.schemas.customers import CustomerCreate, CustomerUpdate, CustomerResponse
from modules.repositories.customer import CustomerRepository

router = APIRouter()


@router.get("/customers", response_model=List[CustomerResponse])
def list_customers(
    keyword: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    repo: CustomerRepository = Depends(get_customer_repo),
):
    return repo.list_customers(keyword=keyword)


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: int,
    repo: CustomerRepository = Depends(get_customer_repo),
):
    customer = repo.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="수급자를 찾을 수 없습니다.")
    return customer


@router.post("/customers", response_model=CustomerResponse, status_code=201)
def create_customer(
    body: CustomerCreate,
    repo: CustomerRepository = Depends(get_customer_repo),
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
    return customer


@router.put("/customers/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: int,
    body: CustomerUpdate,
    repo: CustomerRepository = Depends(get_customer_repo),
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
    return customer


@router.delete("/customers/{customer_id}", status_code=204)
def delete_customer(
    customer_id: int,
    repo: CustomerRepository = Depends(get_customer_repo),
):
    affected = repo.delete_customer(customer_id)
    if not affected:
        raise HTTPException(status_code=404, detail="수급자를 찾을 수 없습니다.")
