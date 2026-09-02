"""
db.py - Supabase (Postgres) data layer for the Ganesh Utsav Receipt
Management System. Reads the connection string from the DATABASE_URL
environment variable (set this on Render / locally before running).
"""

import os
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash

DATABASE_URL = os.environ.get("DATABASE_URL")
RECEIPT_PREFIX = "GU"


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable is not set.")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def _column_names(cur, table):
    cur.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
        (table,),
    )
    return {row["column_name"] for row in cur.fetchall()}


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            id SERIAL PRIMARY KEY,
            receipt_no TEXT UNIQUE NOT NULL,
            date TEXT NOT NULL,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            phone TEXT,
            purpose TEXT NOT NULL DEFAULT 'Ganesh Chanda',
            total_amount DOUBLE PRECISION NOT NULL,
            paid_amount DOUBLE PRECISION NOT NULL DEFAULT 0,
            due_amount DOUBLE PRECISION NOT NULL,
            mode TEXT NOT NULL DEFAULT 'Cash',
            status TEXT NOT NULL DEFAULT 'Unpaid',
            show_qr BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TEXT NOT NULL
        )
    """)
    existing_cols = _column_names(cur, "receipts")
    if "show_qr" not in existing_cols:
        cur.execute("ALTER TABLE receipts ADD COLUMN show_qr BOOLEAN NOT NULL DEFAULT TRUE")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS counters (
            name TEXT PRIMARY KEY,
            value INTEGER NOT NULL
        )
    """)
    cur.execute(
        "INSERT INTO counters (name, value) VALUES ('receipt_no', 0) ON CONFLICT (name) DO NOTHING"
    )

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    defaults = {
        "upi_id": "ganeshutsav@upi",
        "org_name_en": "Sri Sri Vinayaka Utsava Committee",
        "org_name_te": "శ్రీ శ్రీ వినాయక ఉత్సవ కమిటీ",
    }
    for k, v in defaults.items():
        cur.execute(
            "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO NOTHING",
            (k, v),
        )

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'subadmin',
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()

    cur.execute("SELECT COUNT(*) AS c FROM users")
    if cur.fetchone()["c"] == 0:
        admin_user = os.environ.get("ADMIN_USERNAME", "admin")
        admin_pass = os.environ.get("ADMIN_PASSWORD", "akhil1@A")
        cur.execute("""
            INSERT INTO users (username, password_hash, role, created_at)
            VALUES (%s, %s, 'admin', %s)
        """, (admin_user, generate_password_hash(admin_pass), datetime.now().isoformat()))
        conn.commit()

    cur.close()
    conn.close()


def get_setting(key, default=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = %s", (key,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row["value"] if row else default


def next_receipt_no():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE counters SET value = value + 1 WHERE name = 'receipt_no' RETURNING value")
    val = cur.fetchone()["value"]
    conn.commit()
    cur.close()
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
                    phone=None, paid_amount=0.0, date=None, show_qr=True):
    receipt_no = next_receipt_no()
    date = date or datetime.now().strftime("%d-%m-%Y")
    due_amount = round(float(total_amount) - float(paid_amount), 2)
    status = compute_status(float(total_amount), float(paid_amount))

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO receipts
            (receipt_no, date, name, address, phone, purpose,
             total_amount, paid_amount, due_amount, mode, status, show_qr, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (receipt_no, date, name, address, phone, purpose,
          float(total_amount), float(paid_amount), due_amount, mode, status,
          bool(show_qr), datetime.now().isoformat()))
    new_id = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    conn.close()
    return new_id


def get_receipt(receipt_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM receipts WHERE id = %s", (receipt_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def get_receipts_by_ids(ids):
    if not ids:
        return []
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM receipts WHERE id = ANY(%s) ORDER BY id", (list(ids),))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def list_receipts(search=None, status=None):
    query = "SELECT * FROM receipts WHERE 1=1"
    params = []
    if search:
        query += " AND (name ILIKE %s OR receipt_no ILIKE %s)"
        like = f"%{search}%"
        params.extend([like, like])
    if status and status != "All":
        query += " AND status = %s"
        params.append(status)
    query += " ORDER BY id DESC"

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
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
    cur = conn.cursor()
    cur.execute("""
        UPDATE receipts
        SET paid_amount = %s, due_amount = %s, status = %s
        WHERE id = %s
    """, (paid_amount, due, status, receipt_id))
    conn.commit()
    cur.close()
    conn.close()
    return get_receipt(receipt_id)


def mark_paid(receipt_id):
    receipt = get_receipt(receipt_id)
    if not receipt:
        return None
    return update_payment(receipt_id, receipt["total_amount"])


def set_show_qr(receipt_id, show_qr):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE receipts SET show_qr = %s WHERE id = %s", (bool(show_qr), receipt_id))
    conn.commit()
    cur.close()
    conn.close()


def delete_receipt(receipt_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM receipts WHERE id = %s", (receipt_id,))
    conn.commit()
    cur.close()
    conn.close()


def delete_receipts(ids):
    if not ids:
        return
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM receipts WHERE id = ANY(%s)", (list(ids),))
    conn.commit()
    cur.close()
    conn.close()


def all_receipts_as_dicts():
    return [dict(r) for r in list_receipts()]


# --- Users (auth) ---

def get_user_by_username(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def get_user(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def list_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY role DESC, username")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def create_user(username, password, role="subadmin"):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (username, password_hash, role, created_at)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """, (username, generate_password_hash(password), role, datetime.now().isoformat()))
    new_id = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    conn.close()
    return new_id


def delete_user(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()


def update_user_password(user_id, new_password):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET password_hash = %s WHERE id = %s",
                (generate_password_hash(new_password), user_id))
    conn.commit()
    cur.close()
    conn.close()
