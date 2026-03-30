"""청크 업로드 API 전용 테스트 (TestChunkedUpload)."""

import json
from unittest.mock import patch

import pytest

from .conftest import make_mock_daily_info_repo


@pytest.fixture
def mock_repo(app):
    repo = make_mock_daily_info_repo()
    from backend.dependencies import get_daily_info_repo
    app.dependency_overrides[get_daily_info_repo] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_daily_info_repo, None)


class TestChunkedUpload:
    """청크 업로드 API 테스트."""

    # ── 픽스처 ───────────────────────────────────────────────────────────────

    @pytest.fixture(autouse=True)
    def patch_chunk_dir(self, tmp_path):
        """CHUNK_DIR을 임시 디렉토리로 교체해 실제 파일시스템 격리."""
        import backend.routers.upload as upload_mod
        original = upload_mod.CHUNK_DIR
        upload_mod.CHUNK_DIR = tmp_path / "arisa_chunks"
        yield
        upload_mod.CHUNK_DIR = original

    # ── 헬퍼 ─────────────────────────────────────────────────────────────────

    def _init(self, client, filename="test.pdf", chunks=2):
        resp = client.post(
            "/api/upload/chunk/init",
            params={"filename": filename, "total_size": 1024, "total_chunks": chunks},
        )
        return resp.json()["upload_id"]

    def _put_chunk(self, client, upload_id, index, data=b"data"):
        return client.put(
            f"/api/upload/chunk/{upload_id}",
            params={"index": index},
            files={"chunk": ("chunk.bin", data, "application/octet-stream")},
        )

    # ── init ─────────────────────────────────────────────────────────────────

    def test_init_upload_id_반환(self, client, mock_repo):
        import uuid
        resp = client.post(
            "/api/upload/chunk/init",
            params={"filename": "test.pdf", "total_size": 1024, "total_chunks": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "upload_id" in data
        uuid.UUID(data["upload_id"])
        assert data["total_chunks"] == 2

    def test_init_PDF아닌파일_400(self, client, mock_repo):
        resp = client.post(
            "/api/upload/chunk/init",
            params={"filename": "test.txt", "total_size": 100, "total_chunks": 1},
        )
        assert resp.status_code == 400

    def test_init_meta_파일_생성(self, client, mock_repo):
        import backend.routers.upload as upload_mod
        resp = client.post(
            "/api/upload/chunk/init",
            params={"filename": "a.pdf", "total_size": 512, "total_chunks": 1},
        )
        upload_id = resp.json()["upload_id"]
        meta_path = upload_mod.CHUNK_DIR / upload_id / "meta.json"
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text())
        assert meta["filename"] == "a.pdf"
        assert meta["done_chunks"] == []

    # ── upload_chunk ──────────────────────────────────────────────────────────

    def test_청크_업로드_done_chunks_업데이트(self, client, mock_repo):
        upload_id = self._init(client)
        resp = self._put_chunk(client, upload_id, 0)
        assert resp.status_code == 200
        assert 0 in resp.json()["done_chunks"]

    def test_청크_파일_저장됨(self, client, mock_repo):
        import backend.routers.upload as upload_mod
        upload_id = self._init(client)
        self._put_chunk(client, upload_id, 0, b"hello")
        chunk_path = upload_mod.CHUNK_DIR / upload_id / "chunk_000000.bin"
        assert chunk_path.exists()
        assert chunk_path.read_bytes() == b"hello"

    def test_잘못된_청크_인덱스_400(self, client, mock_repo):
        upload_id = self._init(client, chunks=2)
        resp = self._put_chunk(client, upload_id, 99)
        assert resp.status_code == 400

    def test_없는_세션_청크업로드_404(self, client, mock_repo):
        resp = self._put_chunk(client, "nonexistent-id", 0)
        assert resp.status_code == 404

    # ── status ────────────────────────────────────────────────────────────────

    def test_status_done_chunks_반환(self, client, mock_repo):
        upload_id = self._init(client, chunks=3)
        self._put_chunk(client, upload_id, 0)
        self._put_chunk(client, upload_id, 1)
        resp = client.get(f"/api/upload/chunk/{upload_id}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert sorted(data["done_chunks"]) == [0, 1]
        assert data["total_chunks"] == 3

    def test_없는_세션_status_404(self, client, mock_repo):
        resp = client.get("/api/upload/chunk/not-exist/status")
        assert resp.status_code == 404

    # ── complete ──────────────────────────────────────────────────────────────

    def test_complete_파싱_성공(self, client, mock_repo):
        fake_records = [{"customer_name": "홍길동", "date": "2024-01-15"}]
        upload_id = self._init(client, chunks=2)
        self._put_chunk(client, upload_id, 0, b"part0")
        self._put_chunk(client, upload_id, 1, b"part1")
        with patch("modules.pdf_parser.CareRecordParser") as MockParser:
            MockParser.return_value.parse.return_value = fake_records
            resp = client.post(f"/api/upload/chunk/{upload_id}/complete")
        assert resp.status_code == 200
        result = resp.json()
        assert result["file_id"] == upload_id
        assert result["total_records"] == 1
        assert "홍길동" in result["customer_names"]

    def test_complete_청크_누락시_400(self, client, mock_repo):
        upload_id = self._init(client, chunks=2)
        self._put_chunk(client, upload_id, 0)  # 청크 1 누락
        resp = client.post(f"/api/upload/chunk/{upload_id}/complete")
        assert resp.status_code == 400
        assert "누락" in resp.json()["detail"]

    def test_complete_후_임시디렉토리_정리(self, client, mock_repo):
        import backend.routers.upload as upload_mod
        upload_id = self._init(client, chunks=1)
        self._put_chunk(client, upload_id, 0)
        session_dir = upload_mod.CHUNK_DIR / upload_id
        with patch("modules.pdf_parser.CareRecordParser") as MockParser:
            MockParser.return_value.parse.return_value = [{"customer_name": "테스트"}]
            client.post(f"/api/upload/chunk/{upload_id}/complete")
        assert not session_dir.exists()

    def test_complete_파싱_실패시_422(self, client, mock_repo):
        upload_id = self._init(client, chunks=1)
        self._put_chunk(client, upload_id, 0)
        with patch("modules.pdf_parser.CareRecordParser") as MockParser:
            MockParser.return_value.parse.side_effect = Exception("파싱 오류")
            resp = client.post(f"/api/upload/chunk/{upload_id}/complete")
        assert resp.status_code == 422

    def test_complete_후_save_가능(self, client, mock_repo):
        mock_repo.save_parsed_data.return_value = 1
        upload_id = self._init(client, chunks=1)
        self._put_chunk(client, upload_id, 0)
        with patch("modules.pdf_parser.CareRecordParser") as MockParser:
            MockParser.return_value.parse.return_value = [{"customer_name": "홍길동"}]
            client.post(f"/api/upload/chunk/{upload_id}/complete")
        resp = client.post(f"/api/upload/{upload_id}/save")
        assert resp.status_code == 200
        assert resp.json()["saved_count"] == 1
