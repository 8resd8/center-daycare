"""backend/encryption.py 단위 테스트."""

import os
from datetime import date

import pytest

# ENCRYPTION_KEY가 설정되어 있어야 EncryptionService를 import할 수 있음
# conftest.py의 set_test_encryption_key autouse fixture가 처리


from backend.encryption import (
    EncryptionService,
    apply_customer_mask,
    apply_employee_mask,
    is_admin,
    mask_birth_date,
    mask_facility,
    mask_name,
    mask_recognition_no,
)


# ── EncryptionService ────────────────────────────────────────────────


class TestEncryptionService:
    def test_암호화_복호화_왕복(self):
        enc = EncryptionService()
        plaintext = "테스트 문자열"
        token = enc.encrypt(plaintext)
        assert token != plaintext
        assert enc.decrypt(token) == plaintext

    def test_한국어_왕복(self):
        enc = EncryptionService()
        text = "홍길동"
        assert enc.decrypt(enc.encrypt(text)) == text

    def test_빈문자열_왕복(self):
        enc = EncryptionService()
        assert enc.decrypt(enc.encrypt("")) == ""

    def test_safe_decrypt_성공(self):
        enc = EncryptionService()
        token = enc.encrypt("안녕")
        assert enc.safe_decrypt(token) == "안녕"

    def test_safe_decrypt_실패시_원본반환(self):
        enc = EncryptionService()
        assert enc.safe_decrypt("not-a-valid-token") == "not-a-valid-token"

    def test_safe_decrypt_빈값(self):
        enc = EncryptionService()
        assert enc.safe_decrypt("") == ""
        assert enc.safe_decrypt(None) is None  # falsy 처리

    def test_encrypt_optional_None(self):
        enc = EncryptionService()
        assert enc.encrypt_optional(None) is None

    def test_encrypt_optional_값(self):
        enc = EncryptionService()
        result = enc.encrypt_optional("test")
        assert result is not None
        assert enc.decrypt(result) == "test"

    def test_decrypt_optional_None(self):
        enc = EncryptionService()
        assert enc.decrypt_optional(None) is None

    def test_decrypt_optional_값(self):
        enc = EncryptionService()
        token = enc.encrypt("hello")
        assert enc.decrypt_optional(token) == "hello"


# ── mask_name ────────────────────────────────────────────────────────


class TestMaskName:
    def test_일반_이름(self):
        assert mask_name("홍길동") == "홍**"

    def test_두글자_이름(self):
        assert mask_name("이솔") == "이**"

    def test_한글자_이름(self):
        assert mask_name("김") == "김**"

    def test_빈값(self):
        assert mask_name("") == ""

    def test_None(self):
        assert mask_name(None) is None


# ── mask_birth_date ──────────────────────────────────────────────────


class TestMaskBirthDate:
    def test_정상_날짜(self):
        assert mask_birth_date("1990-01-15") == "1990-**-**"

    def test_빈값(self):
        assert mask_birth_date("") == ""

    def test_date_객체(self):
        # str(val).split("-") 로 처리하므로 date 객체도 동작
        assert mask_birth_date(str(date(1990, 1, 15))) == "1990-**-**"

    def test_None(self):
        assert mask_birth_date(None) is None


# ── mask_recognition_no ──────────────────────────────────────────────


class TestMaskRecognitionNo:
    def test_하이픈_있는_형식(self):
        result = mask_recognition_no("2024-01234567")
        assert result == "2024-********"

    def test_하이픈_없는_형식(self):
        result = mask_recognition_no("L1234567890")
        assert result.startswith("L123")
        assert "*" in result

    def test_짧은값(self):
        result = mask_recognition_no("AB")
        assert result == "AB"  # len <= 4 → 원본 반환

    def test_빈값(self):
        assert mask_recognition_no("") == ""

    def test_None(self):
        assert mask_recognition_no(None) is None


# ── mask_facility ────────────────────────────────────────────────────


class TestMaskFacility:
    def test_정상_시설명(self):
        assert mask_facility("보은사랑요양원") == "보은사랑***"

    def test_짧은_이름(self):
        assert mask_facility("AB") == "AB***"

    def test_빈값(self):
        assert mask_facility("") == ""

    def test_None(self):
        assert mask_facility(None) is None


# ── apply_customer_mask ──────────────────────────────────────────────


class TestApplyCustomerMask:
    def test_전체필드_마스킹(self):
        customer = {
            "customer_id": 1,
            "name": "홍길동",
            "birth_date": date(1990, 1, 15),
            "recognition_no": "2024-01234567",
            "facility_name": "보은사랑요양원",
            "facility_code": "BOEUN1234",
            "grade": "3등급",
        }
        masked = apply_customer_mask(customer)
        assert masked["name"] == "홍**"
        assert masked["birth_date"] == "1990-**-**"
        assert "****" in masked["recognition_no"]
        assert masked["facility_name"] == "보은사랑***"
        assert masked["grade"] == "**"
        # customer_id는 마스킹 안됨
        assert masked["customer_id"] == 1

    def test_부분필드만_있을때(self):
        customer = {"customer_id": 2, "name": "이순신"}
        masked = apply_customer_mask(customer)
        assert masked["name"] == "이**"
        assert masked["customer_id"] == 2

    def test_원본_미수정(self):
        customer = {"name": "홍길동", "grade": "3등급"}
        apply_customer_mask(customer)
        assert customer["name"] == "홍길동"
        assert customer["grade"] == "3등급"


# ── apply_employee_mask ──────────────────────────────────────────────


class TestApplyEmployeeMask:
    def test_전체필드_마스킹(self):
        employee = {
            "user_id": 1,
            "name": "김요양",
            "birth_date": date(1990, 5, 1),
            "job_type": "요양보호사",
            "work_status": "재직",
            "hire_date": date(2022, 3, 1),
            "license_name": "요양보호사",
        }
        masked = apply_employee_mask(employee)
        assert masked["name"] == "김**"
        assert masked["birth_date"] == "1990-**-**"
        assert masked["job_type"] == "***"
        assert masked["work_status"] == "***"
        assert masked["hire_date"] == "****-**-**"
        assert masked["license_name"] == "***"

    def test_원본_미수정(self):
        employee = {"name": "김요양", "job_type": "요양보호사"}
        apply_employee_mask(employee)
        assert employee["name"] == "김요양"
        assert employee["job_type"] == "요양보호사"


# ── is_admin ─────────────────────────────────────────────────────────


class TestIsAdmin:
    def test_ADMIN(self):
        assert is_admin({"role": "ADMIN"}) is True

    def test_admin_소문자(self):
        assert is_admin({"role": "admin"}) is True

    def test_VIEWER(self):
        assert is_admin({"role": "VIEWER"}) is False

    def test_빈_dict(self):
        assert is_admin({}) is False

    def test_role_없음(self):
        assert is_admin({"username": "test"}) is False
