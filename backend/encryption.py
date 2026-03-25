"""PII 암호화/복호화 및 마스킹 유틸리티 (AES-128 Fernet)."""

import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


def _load_fernet() -> Fernet:
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise RuntimeError(
            "ENCRYPTION_KEY 환경변수가 설정되지 않았습니다. "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\" "
            "로 키를 생성하고 환경변수에 등록하세요."
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


class EncryptionService:
    """Fernet 대칭 암호화 서비스."""

    def __init__(self):
        self._fernet = _load_fernet()

    def encrypt(self, text: str) -> str:
        """평문 문자열을 암호화하여 base64 토큰으로 반환."""
        return self._fernet.encrypt(text.encode()).decode()

    def decrypt(self, token: str) -> str:
        """암호화 토큰을 복호화하여 평문 문자열로 반환."""
        return self._fernet.decrypt(token.encode()).decode()

    def safe_decrypt(self, value: str) -> str:
        """복호화 시도 후 실패하면 원본 값 그대로 반환 (마이그레이션 과도기용)."""
        if not value:
            return value
        try:
            return self._fernet.decrypt(value.encode()).decode()
        except (InvalidToken, Exception):
            return value

    def encrypt_optional(self, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return self.encrypt(str(value))

    def decrypt_optional(self, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return self.safe_decrypt(value)


# ── 마스킹 함수 (ADMIN 외 역할에 적용) ────────────────────────────────────────

def mask_name(name: str) -> str:
    """홍길동 → 홍**"""
    if not name:
        return name
    return name[0] + "**"


def mask_birth_date(val: str) -> str:
    """1990-01-15 → 1990-**-**"""
    if not val:
        return val
    parts = str(val).split("-")
    if len(parts) >= 1:
        return parts[0] + "-**-**"
    return val


def mask_recognition_no(val: str) -> str:
    """2024-01234567 → 2024-******"""
    if not val:
        return val
    parts = str(val).split("-")
    if len(parts) >= 2:
        return parts[0] + "-" + "*" * len(parts[1])
    return val[:4] + "*" * (len(val) - 4) if len(val) > 4 else val


def mask_facility(val: str) -> str:
    """보은사랑요양원 → 보은사랑***"""
    if not val:
        return val
    visible = min(4, len(val))
    return val[:visible] + "***"


def apply_customer_mask(customer: dict) -> dict:
    """수급자 딕셔너리에 마스킹 적용 (복사본 반환)."""
    masked = dict(customer)
    if masked.get("name"):
        masked["name"] = mask_name(masked["name"])
    if masked.get("birth_date"):
        masked["birth_date"] = mask_birth_date(str(masked["birth_date"]))
    if masked.get("recognition_no"):
        masked["recognition_no"] = mask_recognition_no(masked["recognition_no"])
    if masked.get("facility_name"):
        masked["facility_name"] = mask_facility(masked["facility_name"])
    if masked.get("facility_code"):
        masked["facility_code"] = mask_facility(masked["facility_code"])
    return masked


def apply_employee_mask(employee: dict) -> dict:
    """직원 딕셔너리에 마스킹 적용 (복사본 반환)."""
    masked = dict(employee)
    if masked.get("name"):
        masked["name"] = mask_name(masked["name"])
    if masked.get("birth_date"):
        masked["birth_date"] = mask_birth_date(str(masked["birth_date"]))
    return masked
