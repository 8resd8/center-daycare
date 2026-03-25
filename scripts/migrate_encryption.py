#!/usr/bin/env python
"""
기존 평문 PII 데이터를 Fernet 암호화로 마이그레이션하는 스크립트.

사용법:
  python scripts/migrate_encryption.py --dry-run           # 미리보기 (변경 없음)
  python scripts/migrate_encryption.py --table customers   # customers만
  python scripts/migrate_encryption.py --table users       # users만
  python scripts/migrate_encryption.py                     # 전체 (customers + users)

환경변수:
  ENCRYPTION_KEY  — Fernet 32-byte base64url 키 (필수)
  DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT (옵션, 기본값 localhost/3306)

키 생성:
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

import argparse
import os
import sys

# 프로젝트 루트의 .env 자동 로드
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except ImportError:
    pass

# 프로젝트 루트를 sys.path에 추가
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

import mysql.connector
from cryptography.fernet import Fernet, InvalidToken


# ── 환경변수 로드 ─────────────────────────────────────────────────────────────

def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        print(f"[ERROR] 환경변수 {name} 가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)
    return val


def _get_db_conn():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "arisa"),
        port=int(os.getenv("DB_PORT", "3306")),
        charset="utf8mb4",
    )


# ── 평문 여부 판별 ─────────────────────────────────────────────────────────────

def _is_encrypted(fernet: Fernet, value: str) -> bool:
    """Fernet 복호화 성공 시 True (이미 암호화), 실패 시 False (평문)."""
    try:
        fernet.decrypt(value.encode())
        return True
    except (InvalidToken, Exception):
        return False


# ── 테이블 마이그레이션 ────────────────────────────────────────────────────────

def _migrate_customers(conn, fernet: Fernet, dry_run: bool):
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT customer_id, name, birth_date, recognition_no, facility_name, facility_code "
        "FROM customers"
    )
    rows = cursor.fetchall()
    total = len(rows)
    updated = 0
    skipped = 0
    errors = 0

    for i, row in enumerate(rows, 1):
        cid = row["customer_id"]
        try:
            updates = {}
            for col in ("name", "birth_date", "recognition_no", "facility_name", "facility_code"):
                val = row.get(col)
                if val is None:
                    continue
                val_str = str(val)
                if not _is_encrypted(fernet, val_str):
                    updates[col] = fernet.encrypt(val_str.encode()).decode()

            if not updates:
                skipped += 1
                continue

            if dry_run:
                cols = ", ".join(updates.keys())
                print(f"  [DRY-RUN] customers id={cid} 암호화 예정: {cols}")
            else:
                set_clause = ", ".join(f"{c}=%s" for c in updates)
                update_cur = conn.cursor()
                update_cur.execute(
                    f"UPDATE customers SET {set_clause} WHERE customer_id=%s",
                    (*updates.values(), cid),
                )
                conn.commit()
                update_cur.close()

            updated += 1
        except Exception as e:
            print(f"  [WARN] customers id={cid} 오류 — {e}")
            errors += 1

        if i % 50 == 0 or i == total:
            print(f"  customers 진행: {i}/{total} (업데이트={updated}, 스킵={skipped}, 오류={errors})")

    cursor.close()
    return updated, skipped, errors


def _migrate_users(conn, fernet: Fernet, dry_run: bool):
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT user_id, name, birth_date FROM users")
    rows = cursor.fetchall()
    total = len(rows)
    updated = 0
    skipped = 0
    errors = 0

    for i, row in enumerate(rows, 1):
        uid = row["user_id"]
        try:
            updates = {}
            for col in ("name", "birth_date"):
                val = row.get(col)
                if val is None:
                    continue
                val_str = str(val)
                if not _is_encrypted(fernet, val_str):
                    updates[col] = fernet.encrypt(val_str.encode()).decode()

            if not updates:
                skipped += 1
                continue

            if dry_run:
                cols = ", ".join(updates.keys())
                print(f"  [DRY-RUN] users id={uid} 암호화 예정: {cols}")
            else:
                set_clause = ", ".join(f"{c}=%s" for c in updates)
                update_cur = conn.cursor()
                update_cur.execute(
                    f"UPDATE users SET {set_clause} WHERE user_id=%s",
                    (*updates.values(), uid),
                )
                conn.commit()
                update_cur.close()

            updated += 1
        except Exception as e:
            print(f"  [WARN] users id={uid} 오류 — {e}")
            errors += 1

        if i % 50 == 0 or i == total:
            print(f"  users 진행: {i}/{total} (업데이트={updated}, 스킵={skipped}, 오류={errors})")

    cursor.close()
    return updated, skipped, errors


# ── DDL 실행 ──────────────────────────────────────────────────────────────────

def _run_ddl(conn):
    ddl_path = os.path.join(os.path.dirname(__file__), "alter_columns.sql")
    if not os.path.exists(ddl_path):
        print("[WARN] alter_columns.sql 파일을 찾을 수 없습니다. DDL 건너뜀.")
        return
    with open(ddl_path, encoding="utf-8") as f:
        sql = f.read()

    cursor = conn.cursor()
    # 세미콜론으로 분리하여 각 구문 실행
    for statement in sql.split(";"):
        stmt = statement.strip()
        if stmt and not stmt.startswith("--"):
            try:
                cursor.execute(stmt)
                conn.commit()
            except mysql.connector.Error as e:
                # 이미 존재하는 컬럼 수정 등 무시 가능한 오류
                print(f"  [DDL WARN] {e}")
    cursor.close()
    print("[INFO] DDL 실행 완료.")


# ── 메인 ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="PII 암호화 마이그레이션")
    parser.add_argument("--dry-run", action="store_true", help="변경 없이 미리보기")
    parser.add_argument(
        "--table",
        choices=["customers", "users", "all"],
        default="all",
        help="마이그레이션 대상 테이블 (기본: all)",
    )
    parser.add_argument(
        "--skip-ddl",
        action="store_true",
        help="alter_columns.sql DDL 실행 건너뜀",
    )
    args = parser.parse_args()

    enc_key = _require_env("ENCRYPTION_KEY")
    fernet = Fernet(enc_key.encode())

    print(f"[INFO] 대상: {args.table} | dry-run: {args.dry_run}")

    conn = _get_db_conn()
    print("[INFO] DB 연결 성공.")

    if not args.dry_run and not args.skip_ddl:
        print("[INFO] DDL 실행 중 (컬럼 타입 변경 + audit_logs 테이블 생성)...")
        _run_ddl(conn)

    results = {}

    if args.table in ("customers", "all"):
        print("\n[INFO] customers 마이그레이션 시작...")
        results["customers"] = _migrate_customers(conn, fernet, args.dry_run)

    if args.table in ("users", "all"):
        print("\n[INFO] users 마이그레이션 시작...")
        results["users"] = _migrate_users(conn, fernet, args.dry_run)

    conn.close()

    print("\n── 최종 보고 ─────────────────────────────────────────────")
    for table, (updated, skipped, errors) in results.items():
        mode = "예정" if args.dry_run else "완료"
        print(f"  {table}: 업데이트 {mode} {updated}건 / 이미 암호화 {skipped}건 / 오류 {errors}건")
    print("──────────────────────────────────────────────────────────")


if __name__ == "__main__":
    main()
