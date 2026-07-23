# -*- coding: utf-8 -*-
"""
差旅搭子 - SQLite 数据库层
负责连接管理、建表、CRUD 与统计查询。
采用 Python 内置 sqlite3，文件级嵌入式数据库，无需任何外部服务。
"""
from __future__ import annotations

import os
import sqlite3
import threading
import shutil
from datetime import datetime
from typing import Optional, List, Dict, Any

import config
from db.models import Category, Trip, Invoice, Attachment, Mailbox


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


class InvoiceDB:
    """发票管理数据库访问层（单例连接 + 线程锁）。"""

    def __init__(self, db_path: str = None, attachment_dir: str = None):
        self.db_path = db_path or config.DB_PATH
        self.attachment_dir = attachment_dir or config.ATTACHMENT_DIR
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.attachment_dir, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self.init_schema()
        self.ensure_default_categories()

    # ------------------------------------------------------------------ #
    # 连接 / 事务
    # ------------------------------------------------------------------ #
    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

    def _execute(self, sql: str, params: tuple = ()):
        cur = self._conn.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        return dict(row)

    # ------------------------------------------------------------------ #
    # 建表
    # ------------------------------------------------------------------ #
    def init_schema(self):
        with self._lock:
            cur = self._conn.cursor()
            cur.executescript(
                """
                CREATE TABLE IF NOT EXISTS categories (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    key           TEXT UNIQUE NOT NULL,
                    name          TEXT NOT NULL,
                    icon          TEXT DEFAULT '📄',
                    default_status TEXT DEFAULT 'pending',
                    sort_order    INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS trips (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    name          TEXT NOT NULL,
                    destination   TEXT DEFAULT '',
                    start_date    TEXT DEFAULT '',
                    end_date      TEXT DEFAULT '',
                    budget        REAL DEFAULT 0,
                    note          TEXT DEFAULT '',
                    created_at    TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS invoices (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_code    TEXT DEFAULT '',
                    invoice_number  TEXT DEFAULT '',
                    category_id     INTEGER,
                    amount          REAL DEFAULT 0,
                    tax_amount      REAL DEFAULT 0,
                    amount_excl_tax REAL DEFAULT 0,
                    currency        TEXT DEFAULT 'CNY',
                    issue_date      TEXT DEFAULT '',
                    vendor_name     TEXT DEFAULT '',
                    vendor_tax_id   TEXT DEFAULT '',
                    buyer_name      TEXT DEFAULT '',
                    buyer_tax_id    TEXT DEFAULT '',
                    trip_id         INTEGER,
                    status          TEXT DEFAULT 'pending',
                    payment_method  TEXT DEFAULT '',
                    note            TEXT DEFAULT '',
                    source          TEXT DEFAULT 'manual',
                    source_detail   TEXT DEFAULT '',
                    created_at      TEXT DEFAULT '',
                    updated_at      TEXT DEFAULT '',
                    FOREIGN KEY (category_id) REFERENCES categories(id),
                    FOREIGN KEY (trip_id) REFERENCES trips(id)
                );

                CREATE TABLE IF NOT EXISTS attachments (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id  INTEGER,
                    file_path   TEXT DEFAULT '',
                    file_name   TEXT DEFAULT '',
                    file_type   TEXT DEFAULT '',
                    file_size   INTEGER DEFAULT 0,
                    created_at  TEXT DEFAULT '',
                    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS mailboxes (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT DEFAULT '',
                    host        TEXT DEFAULT '',
                    user        TEXT DEFAULT '',
                    password    TEXT DEFAULT '',
                    use_ssl     INTEGER DEFAULT 1,
                    since_days  INTEGER DEFAULT 30,
                    enabled     INTEGER DEFAULT 1,
                    last_pull   TEXT DEFAULT '',
                    created_at  TEXT DEFAULT ''
                );

                CREATE INDEX IF NOT EXISTS idx_inv_category ON invoices(category_id);
                CREATE INDEX IF NOT EXISTS idx_inv_trip ON invoices(trip_id);
                CREATE INDEX IF NOT EXISTS idx_inv_status ON invoices(status);
                CREATE INDEX IF NOT EXISTS idx_inv_date ON invoices(issue_date);
                CREATE INDEX IF NOT EXISTS idx_inv_number ON invoices(invoice_number);
                CREATE INDEX IF NOT EXISTS idx_att_inv ON attachments(invoice_id);
                """
            )
            self._conn.commit()

    def ensure_default_categories(self):
        with self._lock:
            cur = self._conn.cursor()
            for i, (key, name, icon, status) in enumerate(config.DEFAULT_CATEGORIES):
                cur.execute(
                    "INSERT OR IGNORE INTO categories(key, name, icon, default_status, sort_order) VALUES(?,?,?,?,?)",
                    (key, name, icon, status, i),
                )
            self._conn.commit()

    # ------------------------------------------------------------------ #
    # 分类 categories
    # ------------------------------------------------------------------ #
    def list_categories(self) -> List[Category]:
        cur = self._execute(
            "SELECT * FROM categories ORDER BY sort_order, id"
        )
        return [Category(**self._row_to_dict(r)) for r in cur.fetchall()]

    def get_category(self, cat_id: int) -> Optional[Category]:
        cur = self._execute("SELECT * FROM categories WHERE id=?", (cat_id,))
        r = cur.fetchone()
        return Category(**self._row_to_dict(r)) if r else None

    def get_category_by_key(self, key: str) -> Optional[Category]:
        cur = self._execute("SELECT * FROM categories WHERE key=?", (key,))
        r = cur.fetchone()
        return Category(**self._row_to_dict(r)) if r else None

    # ------------------------------------------------------------------ #
    # 行程 trips
    # ------------------------------------------------------------------ #
    def create_trip(self, trip: Trip) -> int:
        with self._lock:
            cur = self._execute(
                """INSERT INTO trips(name, destination, start_date, end_date, budget, note, created_at)
                   VALUES(?,?,?,?,?,?,?)""",
                (trip.name, trip.destination, trip.start_date, trip.end_date,
                 trip.budget, trip.note, _now()),
            )
            self._conn.commit()
            return cur.lastrowid

    def update_trip(self, trip: Trip):
        with self._lock:
            self._execute(
                """UPDATE trips SET name=?, destination=?, start_date=?, end_date=?,
                   budget=?, note=? WHERE id=?""",
                (trip.name, trip.destination, trip.start_date, trip.end_date,
                 trip.budget, trip.note, trip.id),
            )
            self._conn.commit()

    def delete_trip(self, trip_id: int):
        with self._lock:
            # 先把该行程下的发票置为未归集
            self._execute("UPDATE invoices SET trip_id=NULL WHERE trip_id=?", (trip_id,))
            self._execute("DELETE FROM trips WHERE id=?", (trip_id,))
            self._conn.commit()

    def list_trips(self) -> List[Trip]:
        cur = self._execute("SELECT * FROM trips ORDER BY start_date DESC, id DESC")
        return [Trip(**self._row_to_dict(r)) for r in cur.fetchall()]

    def get_trip(self, trip_id: int) -> Optional[Trip]:
        cur = self._execute("SELECT * FROM trips WHERE id=?", (trip_id,))
        r = cur.fetchone()
        return Trip(**self._row_to_dict(r)) if r else None

    # ------------------------------------------------------------------ #
    # 发票 invoices
    # ------------------------------------------------------------------ #
    def create_invoice(self, inv: Invoice) -> int:
        with self._lock:
            cur = self._execute(
                """INSERT INTO invoices(
                       invoice_code, invoice_number, category_id, amount, tax_amount,
                       amount_excl_tax, currency, issue_date, vendor_name, vendor_tax_id,
                       buyer_name, buyer_tax_id, trip_id, status, payment_method, note,
                       source, source_detail, created_at, updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (inv.invoice_code, inv.invoice_number, inv.category_id, inv.amount,
                 inv.tax_amount, inv.amount_excl_tax, inv.currency, inv.issue_date,
                 inv.vendor_name, inv.vendor_tax_id, inv.buyer_name, inv.buyer_tax_id,
                 inv.trip_id, inv.status, inv.payment_method, inv.note, inv.source,
                 inv.source_detail, _now(), _now()),
            )
            self._conn.commit()
            return cur.lastrowid

    def update_invoice(self, inv: Invoice):
        with self._lock:
            self._execute(
                """UPDATE invoices SET
                       invoice_code=?, invoice_number=?, category_id=?, amount=?, tax_amount=?,
                       amount_excl_tax=?, currency=?, issue_date=?, vendor_name=?, vendor_tax_id=?,
                       buyer_name=?, buyer_tax_id=?, trip_id=?, status=?, payment_method=?, note=?,
                       source=?, source_detail=?, updated_at=?
                   WHERE id=?""",
                (inv.invoice_code, inv.invoice_number, inv.category_id, inv.amount,
                 inv.tax_amount, inv.amount_excl_tax, inv.currency, inv.issue_date,
                 inv.vendor_name, inv.vendor_tax_id, inv.buyer_name, inv.buyer_tax_id,
                 inv.trip_id, inv.status, inv.payment_method, inv.note, inv.source,
                 inv.source_detail, _now(), inv.id),
            )
            self._conn.commit()

    def delete_invoice(self, inv_id: int):
        with self._lock:
            # 删除附件文件
            for att in self.list_attachments(inv_id):
                try:
                    if att.file_path and os.path.exists(att.file_path):
                        os.remove(att.file_path)
                except Exception:
                    pass
            self._execute("DELETE FROM attachments WHERE invoice_id=?", (inv_id,))
            self._execute("DELETE FROM invoices WHERE id=?", (inv_id,))
            self._conn.commit()

    def get_invoice(self, inv_id: int) -> Optional[Invoice]:
        row = self._fetch_invoice_row(inv_id)
        if not row:
            return None
        inv = self._row_to_invoice(row)
        inv.attachments = self.list_attachments(inv_id)
        return inv

    def _fetch_invoice_row(self, inv_id: int):
        cur = self._execute(
            """SELECT i.*, c.name AS category_name, c.icon AS category_icon,
                      t.name AS trip_name
               FROM invoices i
               LEFT JOIN categories c ON i.category_id = c.id
               LEFT JOIN trips t ON i.trip_id = t.id
               WHERE i.id=?""",
            (inv_id,),
        )
        return cur.fetchone()

    def _row_to_invoice(self, row) -> Invoice:
        d = self._row_to_dict(row)
        return Invoice(
            id=d.get("id"),
            invoice_code=d.get("invoice_code", ""),
            invoice_number=d.get("invoice_number", ""),
            category_id=d.get("category_id"),
            category_name=d.get("category_name", "") or "",
            category_icon=d.get("category_icon", "") or "",
            amount=float(d.get("amount") or 0),
            tax_amount=float(d.get("tax_amount") or 0),
            amount_excl_tax=float(d.get("amount_excl_tax") or 0),
            currency=d.get("currency", "CNY"),
            issue_date=d.get("issue_date", "") or "",
            vendor_name=d.get("vendor_name", "") or "",
            vendor_tax_id=d.get("vendor_tax_id", "") or "",
            buyer_name=d.get("buyer_name", "") or "",
            buyer_tax_id=d.get("buyer_tax_id", "") or "",
            trip_id=d.get("trip_id"),
            trip_name=d.get("trip_name", "") or "",
            status=d.get("status", "pending"),
            payment_method=d.get("payment_method", "") or "",
            note=d.get("note", "") or "",
            source=d.get("source", "manual"),
            source_detail=d.get("source_detail", "") or "",
            created_at=d.get("created_at", "") or "",
            updated_at=d.get("updated_at", "") or "",
        )

    def list_invoices(self, filters: Dict[str, Any] = None) -> List[Invoice]:
        """按筛选条件查询发票列表。
        filters 支持：keyword, category_id, trip_id, status,
                     date_from, date_to, source, order_by, desc
        """
        filters = filters or {}
        sql = """SELECT i.*, c.name AS category_name, c.icon AS category_icon,
                        t.name AS trip_name
                 FROM invoices i
                 LEFT JOIN categories c ON i.category_id = c.id
                 LEFT JOIN trips t ON i.trip_id = t.id
                 WHERE 1=1"""
        params = []
        if filters.get("keyword"):
            kw = f"%{filters['keyword']}%"
            sql += """ AND (i.invoice_number LIKE ? OR i.invoice_code LIKE ?
                       OR i.vendor_name LIKE ? OR i.vendor_tax_id LIKE ?
                       OR i.buyer_name LIKE ? OR i.note LIKE ?)"""
            params += [kw, kw, kw, kw, kw, kw]
        if filters.get("category_id"):
            sql += " AND i.category_id = ?"
            params.append(filters["category_id"])
        if filters.get("trip_id"):
            sql += " AND i.trip_id = ?"
            params.append(filters["trip_id"])
        if filters.get("status"):
            sql += " AND i.status = ?"
            params.append(filters["status"])
        if filters.get("source"):
            sql += " AND i.source = ?"
            params.append(filters["source"])
        if filters.get("date_from"):
            sql += " AND i.issue_date >= ?"
            params.append(filters["date_from"])
        if filters.get("date_to"):
            sql += " AND i.issue_date <= ?"
            params.append(filters["date_to"])

        order_by = filters.get("order_by", "issue_date")
        if order_by not in ("issue_date", "amount", "created_at", "updated_at", "id"):
            order_by = "issue_date"
        desc = "DESC" if filters.get("desc", True) else "ASC"
        sql += f" ORDER BY i.{order_by} {desc}, i.id DESC"

        cur = self._execute(sql, tuple(params))
        return [self._row_to_invoice(r) for r in cur.fetchall()]

    def find_duplicate(self, invoice_number: str, invoice_code: str = "",
                       exclude_id: int = None) -> Optional[Invoice]:
        """根据发票号码（及代码）查重，用于导入去重。"""
        if not invoice_number and not invoice_code:
            return None
        sql = "SELECT id FROM invoices WHERE 1=0"
        params = []
        if invoice_number:
            sql = "SELECT id FROM invoices WHERE invoice_number=?"
            params = [invoice_number]
            if invoice_code:
                sql += " AND invoice_code=?"
                params.append(invoice_code)
        else:
            sql = "SELECT id FROM invoices WHERE invoice_code=?"
            params = [invoice_code]
        if exclude_id:
            sql += " AND id<>?"
            params.append(exclude_id)
        cur = self._execute(sql, tuple(params))
        r = cur.fetchone()
        if not r:
            return None
        return self.get_invoice(r["id"])

    # ------------------------------------------------------------------ #
    # 附件 attachments
    # ------------------------------------------------------------------ #
    def add_attachment(self, invoice_id: int, file_path: str,
                       copy_to_storage: bool = True) -> int:
        """保存附件；可选择把文件复制进本地存储目录，返回附件 id。"""
        with self._lock:
            filename = os.path.basename(file_path)
            ext = os.path.splitext(filename)[1].lower().lstrip(".")
            ftype = "pdf" if ext == "pdf" else ("ofd" if ext == "ofd" else "image")
            size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            stored_path = file_path
            if copy_to_storage:
                dest_dir = os.path.join(self.attachment_dir, str(invoice_id))
                os.makedirs(dest_dir, exist_ok=True)
                dest = os.path.join(dest_dir, f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}")
                shutil.copy2(file_path, dest)
                stored_path = dest
            cur = self._execute(
                """INSERT INTO attachments(invoice_id, file_path, file_name, file_type, file_size, created_at)
                   VALUES(?,?,?,?,?,?)""",
                (invoice_id, stored_path, filename, ftype, size, _now()),
            )
            self._conn.commit()
            return cur.lastrowid

    def list_attachments(self, invoice_id: int) -> List[Attachment]:
        cur = self._execute(
            "SELECT * FROM attachments WHERE invoice_id=? ORDER BY id", (invoice_id,)
        )
        return [Attachment(**self._row_to_dict(r)) for r in cur.fetchall()]

    def delete_attachment(self, att_id: int):
        with self._lock:
            cur = self._execute("SELECT * FROM attachments WHERE id=?", (att_id,))
            r = cur.fetchone()
            if r:
                att = Attachment(**self._row_to_dict(r))
                try:
                    if att.file_path and os.path.exists(att.file_path):
                        os.remove(att.file_path)
                except Exception:
                    pass
                self._execute("DELETE FROM attachments WHERE id=?", (att_id,))
                self._conn.commit()

    # ------------------------------------------------------------------ #
    # 设置 settings
    # ------------------------------------------------------------------ #
    def get_setting(self, key: str, default: str = "") -> str:
        cur = self._execute("SELECT value FROM settings WHERE key=?", (key,))
        r = cur.fetchone()
        return r["value"] if r else default

    def set_setting(self, key: str, value: str):
        with self._lock:
            self._execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
            self._conn.commit()

    # ------------------------------------------------------------------ #
    # 邮箱账号 mailboxes
    # ------------------------------------------------------------------ #
    def list_mailboxes(self) -> List[Mailbox]:
        cur = self._execute("SELECT * FROM mailboxes ORDER BY id")
        return [Mailbox(**self._row_to_dict(r)) for r in cur.fetchall()]

    def get_mailbox(self, mb_id: int) -> Optional[Mailbox]:
        cur = self._execute("SELECT * FROM mailboxes WHERE id=?", (mb_id,))
        r = cur.fetchone()
        return Mailbox(**self._row_to_dict(r)) if r else None

    def create_mailbox(self, mb: Mailbox) -> int:
        with self._lock:
            cur = self._execute(
                """INSERT INTO mailboxes(name, host, user, password, use_ssl,
                                         since_days, enabled, last_pull, created_at)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (mb.name, mb.host, mb.user, mb.password,
                 1 if mb.use_ssl else 0, mb.since_days,
                 1 if mb.enabled else 0, mb.last_pull or "", _now()),
            )
            self._conn.commit()
            return cur.lastrowid

    def update_mailbox(self, mb: Mailbox):
        with self._lock:
            self._execute(
                """UPDATE mailboxes SET name=?, host=?, user=?, password=?,
                       use_ssl=?, since_days=?, enabled=? WHERE id=?""",
                (mb.name, mb.host, mb.user, mb.password,
                 1 if mb.use_ssl else 0, mb.since_days,
                 1 if mb.enabled else 0, mb.id),
            )
            self._conn.commit()

    def delete_mailbox(self, mb_id: int):
        with self._lock:
            self._execute("DELETE FROM mailboxes WHERE id=?", (mb_id,))
            self._conn.commit()

    def set_mailbox_last_pull(self, mb_id: int, ts: str):
        with self._lock:
            self._execute("UPDATE mailboxes SET last_pull=? WHERE id=?",
                          (ts, mb_id))
            self._conn.commit()

    def set_attachment_dir(self, path: str):
        """更新附件（下载文件）存储目录并即时生效。"""
        os.makedirs(path, exist_ok=True)
        self.attachment_dir = path
        self.set_setting("attachment_dir", path)

    # ------------------------------------------------------------------ #
    # 统计 stats
    # ------------------------------------------------------------------ #
    def stats_summary(self) -> Dict[str, Any]:
        cur = self._execute(
            "SELECT COUNT(*) AS cnt, COALESCE(SUM(amount),0) AS total FROM invoices"
        )
        r = cur.fetchone()
        total_cnt = r["cnt"]
        total_amt = float(r["total"])

        cur = self._execute(
            "SELECT status, COUNT(*) AS cnt, COALESCE(SUM(amount),0) AS amt "
            "FROM invoices GROUP BY status"
        )
        by_status = {row["status"]: {"count": row["cnt"], "amount": float(row["amt"])}
                     for row in cur.fetchall()}

        pending_amt = by_status.get("pending", {}).get("amount", 0) + \
                      by_status.get("submitted", {}).get("amount", 0)
        reimbursed_amt = by_status.get("reimbursed", {}).get("amount", 0)
        return {
            "total_count": total_cnt,
            "total_amount": total_amt,
            "pending_amount": pending_amt,
            "reimbursed_amount": reimbursed_amt,
            "by_status": by_status,
        }

    def stats_by_category(self) -> List[Dict[str, Any]]:
        cur = self._execute(
            """SELECT c.id AS cat_id, c.name AS name, c.icon AS icon,
                      COUNT(i.id) AS cnt, COALESCE(SUM(i.amount),0) AS total
               FROM categories c
               LEFT JOIN invoices i ON i.category_id = c.id
               GROUP BY c.id ORDER BY total DESC, c.sort_order"""
        )
        return [dict(r) for r in cur.fetchall()]

    def stats_by_trip(self) -> List[Dict[str, Any]]:
        cur = self._execute(
            """SELECT t.id AS trip_id, t.name AS name, t.budget AS budget,
                      COUNT(i.id) AS cnt, COALESCE(SUM(i.amount),0) AS total
               FROM trips t
               LEFT JOIN invoices i ON i.trip_id = t.id
               GROUP BY t.id ORDER BY total DESC, t.start_date DESC"""
        )
        return [dict(r) for r in cur.fetchall()]

    def stats_monthly(self, months: int = 12) -> List[Dict[str, Any]]:
        cur = self._execute(
            """SELECT substr(issue_date,1,7) AS month, COUNT(*) AS cnt,
                      COALESCE(SUM(amount),0) AS total
               FROM invoices
               WHERE issue_date >= date('now', ?)
               GROUP BY month ORDER BY month""",
            (f"-{months - 1} month",),
        )
        return [dict(r) for r in cur.fetchall()]


# 全局单例（延迟初始化）
_db_instance: Optional[InvoiceDB] = None


def get_db() -> InvoiceDB:
    global _db_instance
    if _db_instance is None:
        db = InvoiceDB()
        # 应用已保存的文件存储位置（设置项可覆盖默认目录）
        saved = db.get_setting("attachment_dir", "")
        if saved:
            db.set_attachment_dir(saved)
        _db_instance = db
    return _db_instance
