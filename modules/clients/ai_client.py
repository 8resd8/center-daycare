"""OpenAI 클라이언트 관리 모듈

이 모듈은 다음을 지원하는 AI 클라이언트 관리 기능을 제공합니다:
- Streamlit secrets (프로덕션용)
- 환경변수 (테스트/CLI용)
- 의존성 주입 (단위 테스트용)
"""

import os
import openai
from typing import Optional, Any

# AI Client instance for dependency injection (테스트용)
_ai_client_instance: Optional['AIClient'] = None


class AIClient:
    """OpenAI 클라이언트 래퍼 클래스"""
    
    def __init__(self, client: openai.OpenAI):
        self._client = client
    
    @property
    def client(self) -> openai.OpenAI:
        """OpenAI 클라이언트 인스턴스 반환"""
        return self._client
    
    def chat_completion(self, model: str, messages: list, **kwargs):
        """채팅 완성 요청"""
        return self._client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )


def set_ai_client(client: Optional[Any]) -> None:
    """테스트용 커스텀 AI 클라이언트 설정
    
    Args:
        client: AIClient와 유사한 객체, 또는 초기화를 위해 None
    """
    global _ai_client_instance
    _ai_client_instance = client


def get_api_key() -> str:
    """사용 가능한 소스에서 OpenAI API 키 가져오기
    
    우선순위:
    1. 환경변수 (테스트/CLI용)
    2. Streamlit secrets (프로덕션용)
    
    Returns:
        OpenAI API 키 문자열
    """
    # 환경변수에서 확인
    api_key = os.environ.get('OPENAI_API_KEY')
    if api_key:
        return api_key
    
    # Streamlit secrets에서 확인
    try:
        import streamlit as st
        if hasattr(st, 'secrets'):
            api_key = st.secrets.get("OPENAI_API_KEY")
            if api_key:
                return api_key
    except (ImportError, RuntimeError):
        pass
    
    raise ValueError("OpenAI API 키가 설정되어 있지 않습니다. 환경변수 또는 Streamlit secrets를 설정하세요.")


def get_ai_client() -> AIClient:
    """AI 클라이언트 인스턴스 반환
    
    설정된 커스텀 클라이언트가 있으면 사용하고(테스트용),
    그렇지 않으면 환경변수나 Streamlit secrets의 API 키로 새 클라이언트를 생성합니다.
    
    Streamlit 프로덕션 환경에서는 st.cache_resource를 사용하여 캐시됩니다.
    """
    global _ai_client_instance
    
    # 테스트용 커스텀 클라이언트가 설정되어 있으면 반환
    if _ai_client_instance is not None:
        return _ai_client_instance
    
    # Streamlit 환경인 경우 캐시된 클라이언트 반환
    try:
        import streamlit as st
        return _get_cached_ai_client()
    except (ImportError, RuntimeError):
        pass
    
    # 일반 환경에서는 새 클라이언트 생성
    api_key = get_api_key()
    client = openai.OpenAI(api_key=api_key)
    return AIClient(client)


def _get_cached_ai_client() -> AIClient:
    """Streamlit 환경에서 캐시된 AI 클라이언트 반환"""
    import streamlit as st
    
    @st.cache_resource
    def _create_client():
        api_key = get_api_key()
        client = openai.OpenAI(api_key=api_key)
        return AIClient(client)
    
    return _create_client()
