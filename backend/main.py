"""FastAPI 메인 앱"""

import sys
import os
from contextlib import asynccontextmanager
from pathlib import Path

# modules/ 경로를 Python path에 추가
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.routers import (
    customers,
    employees,
    daily_records,
    weekly_reports,
    ai_evaluations,
    employee_evaluations,
    upload,
    dashboard,
    auth,
)


limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # DB 연결 풀 초기화 (첫 쿼리 시 자동 초기화됨)
    try:
        from modules.db_connection import _get_connection_pool
        _get_connection_pool()
        print("DB 연결 풀 초기화 완료")
    except Exception as e:
        print(f"DB 연결 풀 초기화 실패 (첫 요청 시 재시도): {e}")

    yield

    # 정리 작업
    print("앱 종료")


app = FastAPI(
    title="보은사랑 기록 관리 시스템 API",
    description="요양 시설 기록 관리 REST API",
    version="2.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://arisa.pro",
        "https://www.arisa.pro",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록 — auth는 인증 없이 접근 가능
app.include_router(auth.router, prefix="/api", tags=["인증"])
app.include_router(customers.router, prefix="/api", tags=["수급자"])
app.include_router(employees.router, prefix="/api", tags=["직원"])
app.include_router(daily_records.router, prefix="/api", tags=["일일 기록"])
app.include_router(weekly_reports.router, prefix="/api", tags=["주간 보고서"])
app.include_router(ai_evaluations.router, prefix="/api", tags=["AI 평가"])
app.include_router(employee_evaluations.router, prefix="/api", tags=["직원 평가"])
app.include_router(upload.router, prefix="/api", tags=["파일 업로드"])
app.include_router(dashboard.router, prefix="/api", tags=["대시보드"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0"}


# 프로덕션: React 빌드 파일 서빙
frontend_dist = ROOT_DIR / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")
