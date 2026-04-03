"""직원 피드백 리포트 Repository"""

import json
from typing import Optional, List, Dict
from .base import BaseRepository


class FeedbackReportRepository(BaseRepository):
    def upsert(
        self,
        user_id: int,
        target_month: str,
        admin_note: Optional[str],
        ai_result: dict,
    ) -> int:
        """INSERT … ON DUPLICATE KEY UPDATE → report_id 반환"""
        query = """
            INSERT INTO employee_feedback_reports (user_id, target_month, admin_note, ai_result)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                admin_note = VALUES(admin_note),
                ai_result  = VALUES(ai_result),
                report_id  = LAST_INSERT_ID(report_id)
        """
        return self._execute_transaction_lastrowid(
            query,
            (
                user_id,
                target_month,
                admin_note,
                json.dumps(ai_result, ensure_ascii=False),
            ),
        )

    def get_by_month(self, user_id: int, target_month: str) -> Optional[Dict]:
        """특정 월 리포트 반환. ai_result는 dict로 변환."""
        row = self._execute_query_one(
            "SELECT report_id, user_id, target_month, admin_note, ai_result, "
            "DATE_FORMAT(created_at, '%Y-%m-%dT%H:%i:%s') AS created_at, "
            "DATE_FORMAT(updated_at, '%Y-%m-%dT%H:%i:%s') AS updated_at "
            "FROM employee_feedback_reports "
            "WHERE user_id = %s AND target_month = %s",
            (user_id, target_month),
        )
        if row is None:
            return None
        row = dict(row)
        if isinstance(row.get("ai_result"), str):
            row["ai_result"] = json.loads(row["ai_result"])
        return row

    def list_months(self, user_id: int) -> List[Dict]:
        """저장된 월 목록 (최신순)."""
        rows = self._execute_query(
            "SELECT report_id, target_month, "
            "DATE_FORMAT(created_at, '%Y-%m-%dT%H:%i:%s') AS created_at "
            "FROM employee_feedback_reports "
            "WHERE user_id = %s "
            "ORDER BY target_month DESC",
            (user_id,),
        )
        return [dict(r) for r in rows]
