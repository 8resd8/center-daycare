"""직원 피드백 리포트 서비스 — AI 호출 + DB 저장"""

import json
from typing import Optional, List, Dict

from modules.repositories.feedback_report import FeedbackReportRepository
from modules.clients.ai_client import get_ai_client
from modules.clients.feedback_prompt import FEEDBACK_SYSTEM_PROMPT, build_user_prompt


class FeedbackService:
    """직원 피드백 리포트 서비스 클래스"""

    def __init__(self, repo: FeedbackReportRepository):
        self.repo = repo

    def generate_and_save(
        self,
        user_id: int,
        employee_name: str,
        target_month: str,
        admin_note: Optional[str],
        evaluations: List[Dict],
    ) -> Dict:
        """AI 피드백 생성 → upsert → 저장된 레코드 반환.

        Args:
            user_id: 직원 사용자 ID
            employee_name: 직원 이름
            target_month: 대상 월 (YYYY-MM)
            admin_note: 관리자 노트 (선택사항)
            evaluations: 평가 이력 리스트

        Returns:
            저장된 피드백 레포트 딕셔너리

        Raises:
            ValueError: AI 응답 JSON 파싱 오류
        """
        user_prompt = build_user_prompt(
            employee_name, target_month, admin_note, evaluations
        )
        messages = [
            {"role": "system", "content": FEEDBACK_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        response = get_ai_client().chat_completion(
            model="gemini-2.5-flash-preview-04-17",
            messages=messages,
        )
        content = response.choices[0].message.content
        try:
            ai_result = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"AI 응답 JSON 파싱 오류: {e}") from e

        self.repo.upsert(user_id, target_month, admin_note, ai_result)
        return self.repo.get_by_month(user_id, target_month)

    def list_months(self, user_id: int) -> List[Dict]:
        """특정 직원의 저장된 월 목록 조회.

        Args:
            user_id: 직원 사용자 ID

        Returns:
            월별 리포트 정보 리스트 (최신순)
        """
        return self.repo.list_months(user_id)

    def get_by_month(self, user_id: int, target_month: str) -> Optional[Dict]:
        """특정 월의 피드백 레포트 조회.

        Args:
            user_id: 직원 사용자 ID
            target_month: 대상 월 (YYYY-MM)

        Returns:
            피드백 레포트 딕셔너리 또는 None
        """
        return self.repo.get_by_month(user_id, target_month)
