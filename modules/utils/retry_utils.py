"""재시도 유틸리티 모듈

이 모듈은 다음을 지원하는 재시도 기능을 제공합니다:
- OpenAI API Rate Limit 자동 재시도
- 일반적인 예외에 대한 재시도 로직
- 지수 백오프 및 재시도 정책 설정
"""

import time
from functools import wraps
from typing import Callable, Any, Type, Tuple, Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    wait_random_exponential,
    retry_if_exception_type,
    before_sleep,
    after_log
)
import logging

# 로거 설정
logger = logging.getLogger(__name__)


def openai_retry(max_attempts: int = 5, min_wait: float = 1.0, max_wait: float = 60.0):
    """OpenAI API 호출용 재시도 데코레이터
    
    Args:
        max_attempts: 최대 재시도 횟수 (기본값: 5)
        min_wait: 최소 대기 시간 (초, 기본값: 1.0)
        max_wait: 최대 대기 시간 (초, 기본값: 60.0)
    """
    def decorator(func: Callable) -> Callable:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(Exception),  # 모든 예외에 대해 재시도
            before_sleep=lambda retry_state: logger.warning(
                f"API 호출 실패. {retry_state.outcome.exception()}. "
                f"{retry_state.next_action.sleep:.1f}초 후 재시도... "
                f"({retry_state.attempt_number}/{max_attempts})"
            ),
            reraise=True  # 최종 실패 시 예외 다시 발생
        )
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


def database_retry(max_attempts: int = 3, min_wait: float = 0.5, max_wait: float = 5.0):
    """데이터베이스 연결용 재시도 데코레이터
    
    Args:
        max_attempts: 최대 재시도 횟수 (기본값: 3)
        min_wait: 최소 대기 시간 (초, 기본값: 0.5)
        max_wait: 최대 대기 시간 (초, 기본값: 5.0)
    """
    def decorator(func: Callable) -> Callable:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type((ConnectionError, TimeoutError, Exception)),
            before_sleep=lambda retry_state: logger.warning(
                f"DB 연결 실패. {retry_state.next_action.sleep:.1f}초 후 재시도... "
                f"({retry_state.attempt_number}/{max_attempts})"
            ),
            reraise=True
        )
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


def generic_retry(
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    exponential: bool = True
):
    """범용 재시도 데코레이터
    
    Args:
        exceptions: 재시도할 예외 타입 튜플
        max_attempts: 최대 재시도 횟수
        min_wait: 최소 대기 시간
        max_wait: 최대 대기 시간
        exponential: 지수 백오프 사용 여부
    """
    def decorator(func: Callable) -> Callable:
        if exponential:
            wait_strategy = wait_exponential(multiplier=1, min=min_wait, max=max_wait)
        else:
            wait_strategy = wait_random_exponential(min=min_wait, max=max_wait)
            
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_strategy,
            retry=retry_if_exception_type(exceptions),
            before_sleep=lambda retry_state: logger.warning(
                f"{func.__name__} 실패. {retry_state.next_action.sleep:.1f}초 후 재시도... "
                f"({retry_state.attempt_number}/{max_attempts})"
            ),
            reraise=True
        )
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


def retry_with_backoff(
    func: Callable,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Any:
    """함수를 직접 재시도하는 유틸리티
    
    Args:
        func: 재시도할 함수
        max_attempts: 최대 재시도 횟수
        base_delay: 기본 지연 시간
        max_delay: 최대 지연 시간
        exceptions: 재시도할 예외 타입
        
    Returns:
        함수 실행 결과
        
    Raises:
        마지막 예외
    """
    attempt = 0
    while attempt < max_attempts:
        try:
            return func()
        except exceptions as e:
            attempt += 1
            if attempt >= max_attempts:
                logger.error(f"{func.__name__} 최종 실패: {e}")
                raise
            
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            logger.warning(f"{func.__name__} 실패 ({attempt}/{max_attempts}). {delay:.1f}초 후 재시도...")
            time.sleep(delay)
