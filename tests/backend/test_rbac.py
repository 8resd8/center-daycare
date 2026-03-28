"""비ADMIN 사용자의 쓰기 엔드포인트 403 차단 테스트.

require_admin 의존성이 적용된 모든 엔드포인트에 대해
VIEWER 역할 사용자가 접근 시 403을 반환하는지 검증.
"""

import pytest


class TestCustomerRbac:
    def test_POST_customers_403(self, viewer_client):
        resp = viewer_client.post(
            "/api/customers",
            json={"name": "테스트", "gender": "남"},
        )
        assert resp.status_code == 403

    def test_PUT_customers_403(self, viewer_client):
        resp = viewer_client.put(
            "/api/customers/1",
            json={"name": "테스트"},
        )
        assert resp.status_code == 403

    def test_DELETE_customers_403(self, viewer_client):
        resp = viewer_client.delete("/api/customers/1")
        assert resp.status_code == 403


class TestEmployeeRbac:
    def test_POST_employees_403(self, viewer_client):
        resp = viewer_client.post(
            "/api/employees",
            json={"name": "테스트", "username": "u1", "password": "p1"},
        )
        assert resp.status_code == 403

    def test_PUT_employees_403(self, viewer_client):
        resp = viewer_client.put(
            "/api/employees/1",
            json={"name": "테스트"},
        )
        assert resp.status_code == 403

    def test_DELETE_employees_403(self, viewer_client):
        resp = viewer_client.delete("/api/employees/1")
        assert resp.status_code == 403


class TestDailyRecordRbac:
    def test_DELETE_daily_records_403(self, viewer_client):
        resp = viewer_client.delete("/api/daily-records/1")
        assert resp.status_code == 403


class TestWeeklyReportRbac:
    def test_POST_generate_403(self, viewer_client):
        resp = viewer_client.post(
            "/api/weekly-reports/generate",
            json={
                "customer_id": 1,
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
            },
        )
        assert resp.status_code == 403

    def test_PUT_save_403(self, viewer_client):
        resp = viewer_client.put(
            "/api/weekly-reports/1",
            json={
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
                "report_text": "테스트",
            },
        )
        assert resp.status_code == 403


class TestAiEvaluationRbac:
    def test_POST_evaluate_403(self, viewer_client):
        resp = viewer_client.post(
            "/api/ai-evaluations/evaluate",
            json={
                "record_id": 1,
                "category": "신체",
                "note_text": "테스트",
                "writer_user_id": 1,
            },
        )
        assert resp.status_code == 403

    def test_POST_evaluate_record_403(self, viewer_client):
        resp = viewer_client.post("/api/ai-evaluations/evaluate-record/1")
        assert resp.status_code == 403


class TestEmployeeEvaluationRbac:
    def test_POST_employee_evaluations_403(self, viewer_client):
        resp = viewer_client.post(
            "/api/employee-evaluations",
            json={
                "record_id": 1,
                "target_user_id": 1,
                "category": "신체",
                "evaluation_type": "누락",
                "evaluation_date": "2024-01-15",
                "target_date": "2024-01-10",
                "evaluator_user_id": 2,
            },
        )
        assert resp.status_code == 403

    def test_PUT_employee_evaluations_403(self, viewer_client):
        resp = viewer_client.put(
            "/api/employee-evaluations/1",
            json={
                "category": "신체",
                "evaluation_type": "누락",
            },
        )
        assert resp.status_code == 403

    def test_DELETE_employee_evaluations_403(self, viewer_client):
        resp = viewer_client.delete("/api/employee-evaluations/1")
        assert resp.status_code == 403


class TestUploadRbac:
    def test_POST_upload_403(self, viewer_client):
        resp = viewer_client.post(
            "/api/upload",
            files={"file": ("test.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert resp.status_code == 403

    def test_POST_upload_save_403(self, viewer_client):
        resp = viewer_client.post("/api/upload/test-id/save")
        assert resp.status_code == 403
