"""감사 로그(Audit Log) 저장 리포지토리."""

from typing import Optional
from .base import BaseRepository


class AuditRepository(BaseRepository):
    """audit_logs 테이블에 접근/변경 이벤트를 기록."""

    def log(
        self,
        user_id: int,
        action: str,
        resource: str,
        res_id: Optional[int] = None,
        ip: Optional[str] = None,
    ) -> None:
        """감사 이벤트 삽입. 실패해도 주 요청에 영향 없도록 예외를 삼킴."""
        query = """
            INSERT INTO audit_logs (user_id, action, resource, res_id, ip)
            VALUES (%s, %s, %s, %s, %s)
        """
        try:
            self._execute_transaction(query, (user_id, action, resource, res_id, ip))
        except Exception:
            pass
