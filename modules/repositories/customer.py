from typing import List, Optional, Dict
from .base import BaseRepository
from backend.encryption import EncryptionService


def _get_enc() -> EncryptionService:
    return EncryptionService()


def _decrypt_customer(row: Optional[Dict]) -> Optional[Dict]:
    """DB 행의 PII 컬럼을 복호화하여 반환."""
    if row is None:
        return None
    enc = _get_enc()
    result = dict(row)
    for col in ("name", "birth_date", "recognition_no", "facility_name", "facility_code"):
        if result.get(col) is not None:
            result[col] = enc.safe_decrypt(str(result[col]))
    return result


class CustomerRepository(BaseRepository):
    """Repository for customer-related database operations."""

    def list_customers(self, keyword: str = None) -> List[Dict]:
        """List all customers — 암호화 필드는 Python에서 필터링."""
        query = """
            SELECT customer_id, name, birth_date, gender, recognition_no,
                   benefit_start_date, grade
            FROM customers
            ORDER BY customer_id DESC
        """
        rows = self._execute_query(query)
        decrypted = [_decrypt_customer(r) for r in rows]

        if keyword:
            kw = keyword.lower()
            decrypted = [
                r for r in decrypted
                if (r.get("name") and kw in r["name"].lower())
                or (r.get("recognition_no") and kw in r["recognition_no"].lower())
            ]
        return decrypted

    def get_customer(self, customer_id: int) -> Optional[Dict]:
        """Get a single customer by ID."""
        query = """
            SELECT customer_id, name, birth_date, gender, recognition_no,
                   benefit_start_date, grade
            FROM customers
            WHERE customer_id = %s
        """
        return _decrypt_customer(self._execute_query_one(query, (customer_id,)))

    def create_customer(self, name: str, birth_date, gender: str = None,
                        recognition_no: str = None, benefit_start_date=None,
                        grade: str = None) -> int:
        """Create a new customer and return the ID."""
        enc = _get_enc()
        query = """
            INSERT INTO customers (name, birth_date, gender, recognition_no,
                                   benefit_start_date, grade)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        return self._execute_transaction_lastrowid(
            query,
            (
                enc.encrypt(str(name)),
                enc.encrypt_optional(str(birth_date) if birth_date else None),
                gender,
                enc.encrypt_optional(recognition_no),
                benefit_start_date,
                grade,
            ),
        )

    def update_customer(self, customer_id: int, name: str, birth_date,
                        gender: str = None, recognition_no: str = None,
                        benefit_start_date=None, grade: str = None) -> int:
        """Update a customer and return the number of affected rows."""
        enc = _get_enc()
        query = """
            UPDATE customers
            SET name=%s, birth_date=%s, gender=%s, recognition_no=%s,
                benefit_start_date=%s, grade=%s
            WHERE customer_id=%s
        """
        return self._execute_transaction(
            query,
            (
                enc.encrypt(str(name)),
                enc.encrypt_optional(str(birth_date) if birth_date else None),
                gender,
                enc.encrypt_optional(recognition_no),
                benefit_start_date,
                grade,
                customer_id,
            ),
        )

    def delete_customer(self, customer_id: int) -> int:
        """Delete a customer and return the number of affected rows."""
        query = "DELETE FROM customers WHERE customer_id=%s"
        return self._execute_transaction(query, (customer_id,))

    def find_by_name(self, name: str) -> Optional[Dict]:
        """Find a customer by name — 전체 조회 후 Python 필터링."""
        rows = self._execute_query(
            "SELECT customer_id, name, birth_date, gender, recognition_no, "
            "benefit_start_date, grade FROM customers ORDER BY customer_id DESC"
        )
        for row in rows:
            decrypted = _decrypt_customer(row)
            if decrypted and decrypted.get("name") == name:
                return decrypted
        return None

    def find_by_recognition_no(self, recognition_no: str) -> Optional[Dict]:
        """Find a customer by recognition number — Python 필터링."""
        rows = self._execute_query(
            "SELECT customer_id, name, birth_date, gender, recognition_no, "
            "benefit_start_date, grade FROM customers ORDER BY customer_id DESC"
        )
        for row in rows:
            decrypted = _decrypt_customer(row)
            if decrypted and decrypted.get("recognition_no") == recognition_no:
                return decrypted
        return None

    def find_by_name_and_birth(self, name: str, birth_date) -> Optional[Dict]:
        """Find a customer by name and birth date — Python 필터링."""
        birth_str = str(birth_date) if birth_date else None
        rows = self._execute_query(
            "SELECT customer_id, name, birth_date, gender, recognition_no, "
            "benefit_start_date, grade FROM customers ORDER BY customer_id DESC"
        )
        for row in rows:
            decrypted = _decrypt_customer(row)
            if (
                decrypted
                and decrypted.get("name") == name
                and str(decrypted.get("birth_date", "")) == birth_str
            ):
                return decrypted
        return None

    def get_or_create(self, name: str, birth_date=None, grade: str = None,
                      recognition_no: str = None, facility_name: str = None,
                      facility_code: str = None) -> int:
        """Get existing customer or create a new one."""
        existing = self.find_by_name(name)
        if existing:
            customer_id = existing["customer_id"]
            self.update_customer(
                customer_id=customer_id,
                name=name,
                birth_date=birth_date,
                grade=grade,
                recognition_no=recognition_no,
            )
            return customer_id
        return self.create_customer(
            name=name,
            birth_date=birth_date,
            grade=grade,
            recognition_no=recognition_no,
        )
