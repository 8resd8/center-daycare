"""AI 주간 보고서 작성 모듈 - 서비스 레이어 위임"""

# 서비스 레이어로 위임하기 위한 하위 호환성 래퍼
from modules.services.weekly_report_service import report_service

# 이전 API와의 호환성을 위한 함수
def generate_weekly_report(customer_name, date_range, analysis_payload):
    """주간 보고서 생성 (서비스 위임)"""
    return report_service.generate_weekly_report(customer_name, date_range, analysis_payload)
