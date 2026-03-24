"""PDF 업로드 및 파싱 라우터"""

import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import Dict, List
import io

from backend.dependencies import get_daily_info_repo
from modules.repositories.daily_info import DailyInfoRepository

router = APIRouter()

# 메모리 임시 저장소 (파싱된 결과)
_parsed_cache: Dict[str, List[dict]] = {}


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
):
    """PDF 파싱 → 메모리 보관. file_id 반환."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")

    from modules.pdf_parser import CareRecordParser

    try:
        contents = await file.read()
        pdf_bytes = io.BytesIO(contents)

        parser = CareRecordParser(pdf_bytes)
        records = parser.parse()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"PDF 파싱 실패: {e}")

    if not records:
        raise HTTPException(status_code=422, detail="파싱된 데이터가 없습니다.")

    file_id = str(uuid.uuid4())
    _parsed_cache[file_id] = records

    # 미리보기용 요약
    customer_names = list({r.get("customer_name", "") for r in records})
    return {
        "file_id": file_id,
        "filename": file.filename,
        "total_records": len(records),
        "customer_names": customer_names,
        "records": records,
    }


@router.post("/upload/{file_id}/save")
def save_parsed_data(
    file_id: str,
    repo: DailyInfoRepository = Depends(get_daily_info_repo),
):
    """파싱된 데이터를 DB에 저장"""
    records = _parsed_cache.get(file_id)
    if not records:
        raise HTTPException(status_code=404, detail="파싱 데이터를 찾을 수 없습니다. 다시 업로드하세요.")

    try:
        saved_count = repo.save_parsed_data(records)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB 저장 실패: {e}")

    # 저장 후 캐시에서 제거
    del _parsed_cache[file_id]

    return {"saved_count": saved_count, "message": f"{saved_count}건 저장 완료"}


@router.get("/upload/{file_id}/preview")
def get_parsed_preview(file_id: str):
    """파싱된 데이터 미리보기"""
    records = _parsed_cache.get(file_id)
    if not records:
        raise HTTPException(status_code=404, detail="파싱 데이터를 찾을 수 없습니다.")
    return {"file_id": file_id, "records": records, "total": len(records)}
