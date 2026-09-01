"""
db.py - SQLite data layer for the Ganesh Utsav Receipt Management System.

All database access goes through this module so the rest of the app never
touches raw SQL directly (keeps things modular / testable).
"""

import os
import sqlite3
from datetime import datetime
from pathlib import Path

from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "receipts.db"

RECEIPT_PREFIX = "GU"  # Ganesh Utsav


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables if they don't already exist. Safe to call every startup."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_no TEXT UNIQUE NOT NULL,
            date TEXT NOT NULL,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            phone TEXT,
            purpose TEXT NOT NULL DEFAULT 'Ganesh Chanda',
            total_amount REAL NOT NULL,
            paid_amount REAL NOT NULL DEFAULT 0,
            due_amount REAL NOT NULL,
            mode TEXT NOT NULL DEFAULT 'Cash',
            status TEXT NOT NULL DEFAULT 'Unpaid',
            created_at TEXT NOT NULL
        )
    """)

    # Persistent counter so receipt numbers never repeat/reset even if rows
    # are deleted, and survive across app restarts/years.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS counters (
            name TEXT PRIMARY KEY,
            value INTEGER NOT NULL
        )
    """)
    cur.execute(
        "INSERT OR IGNORE INTO counters (name, value) VALUES ('receipt_no', 0)"
    )

    # Simple app settings (UPI id for the QR code, org names, etc.)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    defaults = {
        "upi_id": "ganeshutsav@upi",
        "org_name_en": "Sri Ganesh Utsav Committee",
        "org_name_te": "శ్రీ గణేష్ ఉత్సవ కమిటీ",
    }
    for k, v in defaults.items():
        cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    # --- Users / authentication ------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'subadmin')),
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()

    # Seed a default admin user the very first time the app runs, so there
    # is always at least one account able to log in and create others.
    # Credentials are taken from environment variables so they can (and
    # should) be overridden in production instead of using the fallback.
    cur.execute("SELECT COUNT(*) AS c FROM users")
    if cur.fetchone()["c"] == 0:
        admin_username = os.environ.get("ADMIN_USERNAME", "admin")
        admin_password = os.environ.get("ADMIN_PASSWORD", "ChangeMe@123")
        cur.execute(
            "INSERT INTO users (username, password_hash, role, created_at) "
            "VALUES (?, ?, 'admin', ?)",
            (admin_username, generate_password_hash(admin_password), datetime.now().isoformat()),
        )
        conn.commit()

    conn.close()


def get_setting(key, default=None):
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def next_receipt_no():
    """Atomically bump the persistent counter and return a formatted receipt no."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE counters SET value = value + 1 WHERE name = 'receipt_no'")
    cur.execute("SELECT value FROM counters WHERE name = 'receipt_no'")
    val = cur.fetchone()["value"]
    conn.commit()
    conn.close()
    year = datetime.now().year
    return f"{RECEIPT_PREFIX}/{year}/{val:04d}"


def compute_status(total_amount, paid_amount):
    if paid_amount <= 0:
        return "Unpaid"
    if paid_amount >= total_amount:
        return "Paid"
    return "Partial"


def create_receipt(name, address, total_amount, mode, purpose="Ganesh Chanda",
                    phone=None, paid_amount=0.0, date=None):
    receipt_no = next_receipt_no()
    date = date or datetime.now().strftime("%d-%m-%Y")
    due_amount = round(float(total_amount) - float(paid_amount), 2)
    status = compute_status(float(total_amount), float(paid_amount))

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO receipts
            (receipt_no, date, name, address, phone, purpose,
             total_amount, paid_amount, due_amount, mode, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (receipt_no, date, name, address, phone, purpose,
          float(total_amount), float(paid_amount), due_amount, mode, status,
          datetime.now().isoformat()))
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return new_id


def get_receipt(receipt_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM receipts WHERE id = ?", (receipt_id,)).fetchone()
    conn.close()
    return row


def list_receipts(search=None, status=None):
    query = "SELECT * FROM receipts WHERE 1=1"
    params = []
    if search:
        query += " AND (name LIKE ? OR receipt_no LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like])
    if status and status != "All":
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY id DESC"

    conn = get_conn()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def update_payment(receipt_id, paid_amount):
    receipt = get_receipt(receipt_id)
    if not receipt:
        return None
    total = receipt["total_amount"]
    paid_amount = max(0.0, float(paid_amount))
    due = round(total - paid_amount, 2)
    status = compute_status(total, paid_amount)

    conn = get_conn()
    conn.execute("""
        UPDATE receipts
        SET paid_amount = ?, due_amount = ?, status = ?
        WHERE id = ?
    """, (paid_amount, due, status, receipt_id))
    conn.commit()
    conn.close()
    return get_receipt(receipt_id)


def mark_paid(receipt_id):
    receipt = get_receipt(receipt_id)
    if not receipt:
        return None
    return update_payment(receipt_id, receipt["total_amount"])


def delete_receipt(receipt_id):
    conn = get_conn()
    conn.execute("DELETE FROM receipts WHERE id = ?", (receipt_id,))
    conn.commit()
    conn.close()


def all_receipts_as_dicts():
    return [dict(r) for r in list_receipts()]


# ---------------------------------------------------------------------------
# Users / authentication
# ---------------------------------------------------------------------------

def create_user(username, password, role):
    if role not in ("admin", "subadmin"):
        raise ValueError("Role must be 'admin' or 'subadmin'.")
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
            (username, generate_password_hash(password), role, datetime.now().isoformat()),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError(f"Username '{username}' is already taken.")
    finally:
        conn.close()


def get_user(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def get_user_by_username(username):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return row


def verify_user(username, password):
    """Return the user row if credentials are correct, otherwise None."""
    row = get_user_by_username(username)
    if not row:
        return None
    if not check_password_hash(row["password_hash"], password):
        return None
    return row


def list_users():
    conn = get_conn()
    rows = conn.execute("SELECT id, username, role, created_at FROM users ORDER BY id").fetchall()
    conn.close()
    return rows


def count_admins():
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'admin'").fetchone()
    conn.close()
    return row["c"]


def delete_user(user_id):
    conn = get_conn()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()