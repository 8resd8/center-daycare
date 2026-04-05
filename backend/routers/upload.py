"""PDF 업로드 및 파싱 라우터"""

import asyncio
import io
import json
import logging
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

logger = logging.getLogger(__name__)

from backend.dependencies import get_current_user, get_daily_info_repo, require_admin
from modules.repositories.daily_info import DailyInfoRepository

router = APIRouter(dependencies=[Depends(get_current_user)])

# 메모리 임시 저장소 (파싱된 결과)
_parsed_cache: Dict[str, List[dict]] = {}

# 청크 임시 저장 디렉토리
CHUNK_DIR = Path(tempfile.gettempdir()) / "arisa_chunks"
CHUNK_TTL_HOURS = 2


# ─── 헬퍼 ───────────────────────────────────────────────────────────────────


def _get_session_dir(upload_id: str) -> Path:
    return CHUNK_DIR / upload_id


def _read_meta(upload_id: str) -> dict:
    meta_path = _get_session_dir(upload_id) / "meta.json"
    if not meta_path.exists():
        raise HTTPException(
            status_code=404, detail="업로드 세션을 찾을 수 없습니다. 다시 시작하세요."
        )
    return json.loads(meta_path.read_text(encoding="utf-8"))


def _write_meta(upload_id: str, meta: dict) -> None:
    (_get_session_dir(upload_id) / "meta.json").write_text(
        json.dumps(meta), encoding="utf-8"
    )


def _cleanup_expired_sessions() -> None:
    """CHUNK_TTL_HOURS 초과된 청크 세션 자동 삭제."""
    if not CHUNK_DIR.exists():
        return
    now = datetime.now(timezone.utc)
    for session_dir in CHUNK_DIR.iterdir():
        meta_path = session_dir / "meta.json"
        if not meta_path.exists():
            shutil.rmtree(session_dir, ignore_errors=True)
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            created_at = datetime.fromisoformat(meta["created_at"])
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            age_hours = (now - created_at).total_seconds() / 3600
            if age_hours > CHUNK_TTL_HOURS:
                shutil.rmtree(session_dir, ignore_errors=True)
        except Exception:
            shutil.rmtree(session_dir, ignore_errors=True)


# ─── 기존 단일 업로드 엔드포인트 ────────────────────────────────────────────


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    _: dict = Depends(require_admin),
):
    """PDF 파싱 → 메모리 보관. file_id 반환."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")

    from modules.pdf_parser import CareRecordParser

    try:
        contents = await file.read()
        pdf_bytes = io.BytesIO(contents)

        parser = CareRecordParser(pdf_bytes)
        records = await asyncio.to_thread(parser.parse)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"PDF 파싱 실패: {e}")

    if not records:
        raise HTTPException(status_code=422, detail="파싱된 데이터가 없습니다.")

    file_id = str(uuid.uuid4())
    _parsed_cache[file_id] = records

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
    _: dict = Depends(require_admin),
):
    """파싱된 데이터를 DB에 저장"""
    records = _parsed_cache.get(file_id)
    if not records:
        raise HTTPException(
            status_code=404, detail="파싱 데이터를 찾을 수 없습니다. 다시 업로드하세요."
        )

    try:
        saved_count = repo.save_parsed_data(records)
    except Exception as e:
        logger.error("DB 저장 실패 (file_id=%s): %s", file_id, e)
        raise HTTPException(status_code=500, detail="DB 저장 중 오류가 발생했습니다.")

    del _parsed_cache[file_id]

    return {"saved_count": saved_count, "message": f"{saved_count}건 저장 완료"}


@router.get("/upload/{file_id}/preview")
def get_parsed_preview(file_id: str):
    """파싱된 데이터 미리보기"""
    records = _parsed_cache.get(file_id)
    if not records:
        raise HTTPException(status_code=404, detail="파싱 데이터를 찾을 수 없습니다.")
    return {"file_id": file_id, "records": records, "total": len(records)}


# ─── 청크 업로드 엔드포인트 ─────────────────────────────────────────────────


@router.post("/upload/chunk/init")
async def init_chunked_upload(
    filename: str,
    total_size: int,
    total_chunks: int,
    _: dict = Depends(require_admin),
):
    """청크 업로드 세션 초기화. upload_id 반환."""
    _cleanup_expired_sessions()

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")

    upload_id = str(uuid.uuid4())
    session_dir = _get_session_dir(upload_id)
    session_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "upload_id": upload_id,
        "filename": filename,
        "total_size": total_size,
        "total_chunks": total_chunks,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "done_chunks": [],
    }
    _write_meta(upload_id, meta)

    return {"upload_id": upload_id, "total_chunks": total_chunks}


@router.put("/upload/chunk/{upload_id}")
async def upload_chunk(
    upload_id: str,
    index: int,
    chunk: UploadFile = File(...),
    _: dict = Depends(require_admin),
):
    """청크 하나를 업로드. 이미 완료된 청크는 덮어쓰기 허용 (재시도 안전)."""
    meta = _read_meta(upload_id)

    if index < 0 or index >= meta["total_chunks"]:
        raise HTTPException(status_code=400, detail=f"잘못된 청크 인덱스: {index}")

    chunk_path = _get_session_dir(upload_id) / f"chunk_{index:06d}.bin"
    data = await chunk.read()
    chunk_path.write_bytes(data)

    if index not in meta["done_chunks"]:
        meta["done_chunks"].append(index)
    _write_meta(upload_id, meta)

    return {
        "upload_id": upload_id,
        "done_chunks": meta["done_chunks"],
        "total_chunks": meta["total_chunks"],
    }


@router.get("/upload/chunk/{upload_id}/status")
async def get_chunk_status(upload_id: str):
    """현재까지 업로드된 청크 목록 반환. 이어올리기 용도."""
    meta = _read_meta(upload_id)
    return {
        "upload_id": upload_id,
        "done_chunks": meta["done_chunks"],
        "total_chunks": meta["total_chunks"],
        "filename": meta["filename"],
    }


@router.post("/upload/chunk/{upload_id}/complete")
async def complete_chunked_upload(
    upload_id: str,
    _: dict = Depends(require_admin),
):
    """모든 청크를 합쳐 PDF 파싱. 기존 /upload 응답과 동일한 구조 반환."""
    meta = _read_meta(upload_id)

    total_chunks = meta["total_chunks"]
    done_chunks = sorted(meta["done_chunks"])

    if len(done_chunks) != total_chunks or done_chunks != list(range(total_chunks)):
        missing = sorted(set(range(total_chunks)) - set(done_chunks))
        raise HTTPException(
            status_code=400,
            detail=f"누락된 청크: {missing[:10]}{'...' if len(missing) > 10 else ''}",
        )

    # 청크 합치기
    session_dir = _get_session_dir(upload_id)
    pdf_buffer = io.BytesIO()
    for i in range(total_chunks):
        chunk_path = session_dir / f"chunk_{i:06d}.bin"
        if not chunk_path.exists():
            raise HTTPException(status_code=400, detail=f"청크 파일 없음: {i}")
        pdf_buffer.write(chunk_path.read_bytes())
    pdf_buffer.seek(0)

    from modules.pdf_parser import CareRecordParser

    try:
        parser = CareRecordParser(pdf_buffer)
        records = await asyncio.to_thread(parser.parse)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"PDF 파싱 실패: {e}")
    finally:
        # 파싱 성공·실패 무관하게 임시 청크 정리
        shutil.rmtree(session_dir, ignore_errors=True)

    if not records:
        raise HTTPException(status_code=422, detail="파싱된 데이터가 없습니다.")

    # 기존 캐시에 동일 upload_id로 저장 (save 엔드포인트 재사용)
    _parsed_cache[upload_id] = records

    customer_names = list({r.get("customer_name", "") for r in records})
    return {
        "file_id": upload_id,
        "filename": meta["filename"],
        "total_records": len(records),
        "customer_names": customer_names,
        "records": records,
    }
