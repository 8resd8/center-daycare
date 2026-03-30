"""PDF 업로드 API 테스트."""

import io
import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from .conftest import make_mock_daily_info_repo


@pytest.fixture
def mock_repo(app):
    repo = make_mock_daily_info_repo()
    from backend.dependencies import get_daily_info_repo
    app.dependency_overrides[get_daily_info_repo] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_daily_info_repo, None)


class TestUploadPdf:
    def test_PDF_아닌_파일_400(self, client, mock_repo):
        data = io.BytesIO(b"not a pdf")
        resp = client.post(
            "/api/upload",
            files={"file": ("test.txt", data, "text/plain")},
        )
        assert resp.status_code == 400
        assert "PDF" in resp.json()["detail"]

    def test_파싱_실패_422(self, client, mock_repo):
        with patch("modules.pdf_parser.CareRecordParser") as MockParser:
            MockParser.return_value.parse.side_effect = Exception("파싱 오류")
            data = io.BytesIO(b"%PDF-1.4 fake content")
            resp = client.post(
                "/api/upload",
                files={"file": ("test.pdf", data, "application/pdf")},
            )
        assert resp.status_code == 422
        assert "파싱 실패" in resp.json()["detail"]

    def test_파싱_결과_없을때_422(self, client, mock_repo):
        with patch("modules.pdf_parser.CareRecordParser") as MockParser:
            MockParser.return_value.parse.return_value = []
            data = io.BytesIO(b"%PDF-1.4 fake content")
            resp = client.post(
                "/api/upload",
                files={"file": ("test.pdf", data, "application/pdf")},
            )
        assert resp.status_code == 422
        assert "파싱된 데이터가 없습니다" in resp.json()["detail"]

    def test_PDF_업로드_성공(self, client, mock_repo):
        fake_records = [
            {"customer_name": "홍길동", "date": "2024-01-15"},
            {"customer_name": "홍길동", "date": "2024-01-16"},
        ]
        with patch("modules.pdf_parser.CareRecordParser") as MockParser:
            MockParser.return_value.parse.return_value = fake_records
            data = io.BytesIO(b"%PDF-1.4 fake content")
            resp = client.post(
                "/api/upload",
                files={"file": ("test.pdf", data, "application/pdf")},
            )
        assert resp.status_code == 200
        result = resp.json()
        assert "file_id" in result
        assert result["total_records"] == 2
        assert "홍길동" in result["customer_names"]
        assert len(result["records"]) == 2

    def test_업로드_후_file_id_UUID_형식(self, client, mock_repo):
        import uuid
        with patch("modules.pdf_parser.CareRecordParser") as MockParser:
            MockParser.return_value.parse.return_value = [{"customer_name": "test"}]
            data = io.BytesIO(b"%PDF fake")
            resp = client.post(
                "/api/upload",
                files={"file": ("test.pdf", data, "application/pdf")},
            )
        file_id = resp.json()["file_id"]
        # UUID 형식 검증
        uuid.UUID(file_id)  # 예외 없으면 통과


class TestSaveParsedData:
    def _upload_and_get_file_id(self, client, mock_repo):
        """업로드 후 file_id 반환."""
        with patch("modules.pdf_parser.CareRecordParser") as MockParser:
            MockParser.return_value.parse.return_value = [{"customer_name": "홍길동"}]
            data = io.BytesIO(b"%PDF fake")
            resp = client.post(
                "/api/upload",
                files={"file": ("test.pdf", data, "application/pdf")},
            )
        return resp.json()["file_id"]

    def test_저장_성공(self, client, mock_repo):
        file_id = self._upload_and_get_file_id(client, mock_repo)
        mock_repo.save_parsed_data.return_value = 1

        resp = client.post(f"/api/upload/{file_id}/save")
        assert resp.status_code == 200
        assert resp.json()["saved_count"] == 1

    def test_없는_file_id_404(self, client, mock_repo):
        resp = client.post("/api/upload/nonexistent-id/save")
        assert resp.status_code == 404

    def test_저장_후_캐시_삭제(self, client, mock_repo):
        """저장 후 같은 file_id로 다시 저장 시도하면 404."""
        file_id = self._upload_and_get_file_id(client, mock_repo)
        mock_repo.save_parsed_data.return_value = 1

        client.post(f"/api/upload/{file_id}/save")
        # 두 번째 저장 시도
        resp = client.post(f"/api/upload/{file_id}/save")
        assert resp.status_code == 404

    def test_DB_저장_실패_500(self, client, mock_repo):
        file_id = self._upload_and_get_file_id(client, mock_repo)
        mock_repo.save_parsed_data.side_effect = Exception("DB 오류")

        resp = client.post(f"/api/upload/{file_id}/save")
        assert resp.status_code == 500
        assert "DB 저장 실패" in resp.json()["detail"]


class TestGetParsedPreview:
    def test_미리보기_반환(self, client, mock_repo):
        with patch("modules.pdf_parser.CareRecordParser") as MockParser:
            MockParser.return_value.parse.return_value = [{"customer_name": "홍길동"}]
            data = io.BytesIO(b"%PDF fake")
            upload_resp = client.post(
                "/api/upload",
                files={"file": ("test.pdf", data, "application/pdf")},
            )
        file_id = upload_resp.json()["file_id"]

        resp = client.get(f"/api/upload/{file_id}/preview")
        assert resp.status_code == 200
        result = resp.json()
        assert result["file_id"] == file_id
        assert result["total"] == 1

    def test_없는_file_id_404(self, client, mock_repo):
        resp = client.get("/api/upload/nonexistent/preview")
        assert resp.status_code == 404
