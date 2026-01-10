"""데이터베이스 연결 유틸리티 및 컨텍스트 매니저

이 모듈은 다음을 지원하는 데이터베이스 연결 관리 기능을 제공합니다:
- Streamlit secrets (프로덕션용)
- 환경변수 (테스트/CLI용)
- 의존성 주입 (단위 테스트용)
"""

import os
import mysql.connector
from contextlib import contextmanager
from typing import Iterator, Optional, Callable, Dict, Any

# Connection factory for dependency injection (테스트용)
_connection_factory: Optional[Callable[[], Any]] = None


def set_connection_factory(factory: Optional[Callable[[], Any]]) -> None:
    """테스트용 커스텀 연결 팩토리 설정
    
    Args:
        factory: 연결과 유사한 객체를 반환하는 호출 가능한 객체, 또는 초기화를 위해 None
    """
    global _connection_factory
    _connection_factory = factory


def get_db_config() -> Dict[str, Any]:
    """사용 가능한 소스에서 데이터베이스 설정 가져오기
    
    우선순위:
    1. 환경변수 (테스트/CLI용)
    2. Streamlit secrets (프로덕션용)
    
    Returns:
        데이터베이스 설정 딕셔너리
    """
    # 환경변수에서 설정 확인
    if os.environ.get('DB_HOST'):
        return {
            'host': os.environ.get('DB_HOST'),
            'port': int(os.environ.get('DB_PORT', 3306)),
            'user': os.environ.get('DB_USER'),
            'password': os.environ.get('DB_PASSWORD'),
            'database': os.environ.get('DB_NAME'),
        }
    
    # Streamlit secrets에서 설정 확인
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and 'mysql' in st.secrets:
            return dict(st.secrets["mysql"])
    except (ImportError, RuntimeError):
        pass
    
    raise RuntimeError("Database configuration not found. Set environment variables or Streamlit secrets.")


def get_db_connection():
    """데이터베이스 연결 가져오기
    
    설정된 커스텀 팩토리가 있으면 사용하고(테스트용),
    그렇지 않으면 환경변수나 Streamlit secrets의 설정을 사용합니다.
    """
    if _connection_factory is not None:
        return _connection_factory()
    
    config = get_db_config()
    return mysql.connector.connect(**config)


@contextmanager
def db_transaction(dictionary: bool = False) -> Iterator[mysql.connector.cursor.MySQLCursor]:
    """자동 커밋/롤백이 포함된 데이터베이스 트랜잭션 컨텍스트 매니저
    
    Args:
        dictionary: 딕셔너리 커서 반환 여부 (기본값: False)
        
    Yields:
        MySQL 커서 객체
        
    Usage:
        with db_transaction() as cursor:
            cursor.execute("INSERT INTO table VALUES (%s)", (value,))
            # 성공 시 자동 커밋, 예외 발생 시 롤백
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=dictionary)
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


@contextmanager
def db_query(dictionary: bool = True) -> Iterator[mysql.connector.cursor.MySQLCursor]:
    """읽기 전용 데이터베이스 쿼리용 컨텍스트 매니저
    
    Args:
        dictionary: 딕셔너리 커서 반환 여부 (기본값: True)
        
    Yields:
        MySQL 커서 객체
        
    Usage:
        with db_query() as cursor:
            cursor.execute("SELECT * FROM table WHERE id = %s", (id,))
            results = cursor.fetchall()
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=dictionary)
    try:
        yield cursor
    finally:
        cursor.close()
        conn.close()
