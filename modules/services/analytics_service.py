"""분석 서비스 - 주간 데이터 분석 비즈니스 로직"""

from typing import Dict, List, Tuple, Optional
from datetime import date
import modules.weekly_data_analyzer as analyzer


class AnalyticsService:
    """분석 서비스 클래스 - weekly_data_analyzer의 함수들을 위임하는 래퍼"""
    
    def compute_weekly_status(self, customer_name: str, week_start_str: str, customer_id: int) -> Dict:
        """고객의 주간 상태 계산
        
        Args:
            customer_name: 고객명
            week_start_str: 주 시작일 문자열 (YYYY-MM-DD)
            customer_id: 고객 ID
            
        Returns:
            주간 상태 분석 결과 딕셔너리
        """
        return analyzer.compute_weekly_status(customer_name, week_start_str, customer_id)
    
    def analyze_weekly_trend(self, records: List[Dict], prev_range: Tuple[date, date], 
                           curr_range: Tuple[date, date], customer_id: int) -> Dict:
        """주간 트렌드 분석
        
        Args:
            records: 기록 목록
            prev_range: 이전 주 날짜 범위
            curr_range: 현재 주 날짜 범위
            customer_id: 고객 ID
            
        Returns:
            트렌드 분석 결과 딕셔너리
        """
        return analyzer.analyze_weekly_trend(records, prev_range, curr_range, customer_id)
    
    def score_text(self, text: Optional[str]) -> int:
        """텍스트 점수 계산
        
        Args:
            text: 평가할 텍스트
            
        Returns:
            0-100 사이의 점수
        """
        return analyzer._score_text(text)
    
    def fetch_two_week_records(self, name: str, start_date: date) -> Tuple[List[Dict], Tuple[date, date], Tuple[date, date]]:
        """2주간의 기록 가져오기
        
        Args:
            name: 고객명
            start_date: 시작일
            
        Returns:
            (기록 목록, 이전 주 범위, 현재 주 범위) 튜플
        """
        return analyzer._fetch_two_week_records(name, start_date)
    
    def detect_meal_type(self, text: Optional[str]) -> Optional[str]:
        """식사 유형 감지
        
        Args:
            text: 식사 관련 텍스트
            
        Returns:
            식사 유형 또는 None
        """
        return analyzer._detect_meal_type(text)
    
    def score_meal_amount(self, text: Optional[str]) -> float:
        """식사량 점수 계산
        
        Args:
            text: 식사량 관련 텍스트
            
        Returns:
            식사량 점수 (0.0-1.0)
        """
        return analyzer._score_meal_amount(text)
    
    def meal_amount_label(self, text: Optional[str]) -> str:
        """식사량 레이블 반환
        
        Args:
            text: 식사량 관련 텍스트
            
        Returns:
            식사량 레이블
        """
        return analyzer._meal_amount_label(text)
    
    def extract_toilet_count(self, text: Optional[str]) -> Optional[float]:
        """배설 횟수 추출
        
        Args:
            text: 배설 관련 텍스트
            
        Returns:
            배설 횟수 또는 None
        """
        return analyzer._extract_toilet_count(text)
    
    def parse_toilet_breakdown(self, text: Optional[str]) -> Dict[str, float]:
        """배설 상세 분석
        
        Args:
            text: 배설 관련 텍스트
            
        Returns:
            배설 유형별 횟수 딕셔너리
        """
        return analyzer._parse_toilet_breakdown(text)


# 서비스 인스턴스 생성
analytics_service = AnalyticsService()
