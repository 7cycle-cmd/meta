"""sql.py — value.db 存取層（值資產 + 拆分 + terminology 授權）"""

import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\value\value.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(";\n".join([
            VALUE_DDL, SPLIT_TOTAL_DDL, SPLIT_VALUE_DDL, TERMINOLOGY_DDL,
        ]))
        self.conn.commit()

    def add(self, value, taxonomy_id=None):
        """新增 / 攞一個值嘅 id（冪等；taxonomy_id = 邊個 module 登記）"""
        r = self.conn.execute(
            "SELECT id FROM value WHERE value IS ?", (value,)).fetchone()
        if r:
            if taxonomy_id is not None:
                self.conn.execute(
                    "UPDATE value SET taxonomy_id = ?"
                    " WHERE id = ? AND taxonomy_id IS NULL",
                    (taxonomy_id, r["id"]))
                self.conn.commit()
            return r["id"]
        cur = self.conn.execute(
            "INSERT INTO value (value, taxonomy_id) VALUES (?, ?)",
            (value, taxonomy_id))
        self.conn.commit()
        return cur.lastrowid

    def get(self, value_id):
        """按 id 攞一個值"""
        r = self.conn.execute(
            "SELECT * FROM value WHERE id = ?", (value_id,)).fetchone()
        return dict(r) if r else None

    def by_value(self, value):
        """按值攞行（唔存在 None）"""
        r = self.conn.execute(
            "SELECT * FROM value WHERE value IS ?", (value,)).fetchone()
        return dict(r) if r else None

    def list(self, taxonomy_id=None, active_only=True):
        """列出值（可按 module 篩選）"""
        sql = "SELECT * FROM value WHERE 1=1"
        args = []
        if taxonomy_id is not None:
            sql += " AND taxonomy_id = ?"
            args.append(taxonomy_id)
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    # ---------- split_total + split_value（2026-10-28 用戶要求） ----------
    def add_split(self, value_id, parts):
        """拆分一個值（自動寫 split_total + split_value）

        parts = [str, str, ...]（拆出嚟嘅值，次序 = seq）
        返回 {"split_total_id": n, "split_values": [id, ...]}
        """
        if not parts:
            raise ValueError("parts 唔可以空")
        # common.seq.id（次序字典）：攞 seq id（1..n 對應）
        seq_ids = []
        try:
            c = sqlite3.connect(r"C:\projects\meta\common\common.db")
            c.row_factory = sqlite3.Row
            try:
                for i in range(1, len(parts) + 1):
                    r = c.execute(
                        "SELECT id FROM seq WHERE value = ?", (i,)).fetchone()
                    seq_ids.append(r["id"] if r else i)
            finally:
                c.close()
        except Exception:
            seq_ids = list(range(1, len(parts) + 1))
        # json 快照（用戶指定格式）
        snap = ";".join(
            f'"split_value":"{p}, seq={i}"' for i, p in enumerate(parts, 1))
        total_json = "[" + snap + (";" if parts else "") + "]"
        # 1. split_total
        cur = self.conn.execute(
            "INSERT INTO split_total (value_id, split_total, json)"
            " VALUES (?, ?, ?)", (value_id, len(parts), total_json))
        stid = cur.lastrowid
        # 2. split_value（每份一行）
        sv_ids = []
        for i, p in enumerate(parts, 1):
            vjson = f'["split_value":"{p}, seq={i}";]'
            c2 = self.conn.execute(
                "INSERT INTO split_value"
                " (value_id, split_total_id, split_value, seq_id, json)"
                " VALUES (?, ?, ?, ?, ?)",
                (value_id, stid, p, seq_ids[i - 1], vjson))
            sv_ids.append(c2.lastrowid)
        self.conn.commit()
        return {"split_total_id": stid, "split_values": sv_ids}

    def split_totals(self, value_id=None, active_only=True):
        """列出拆分總覽（可按值篩選）"""
        sql = "SELECT * FROM split_total WHERE 1=1"
        args = []
        if value_id is not None:
            sql += " AND value_id = ?"
            args.append(value_id)
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id DESC"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def split_values(self, split_total_id=None, value_id=None,
                     active_only=True):
        """列出拆分值（可按拆分 / 值篩選）"""
        sql = "SELECT * FROM split_value WHERE 1=1"
        args = []
        if split_total_id is not None:
            sql += " AND split_total_id = ?"
            args.append(split_total_id)
        if value_id is not None:
            sql += " AND value_id = ?"
            args.append(value_id)
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY seq_id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    # ---------- terminology 授權（2026-10-28 用戶要求） ----------
    def grant_terminology(self, terminology_id, split_value_id):
        """授權一個拆分值有權 call terminology（冪等）

        REST_API_WRITE -> 127.0.0.1:8500/word-proof?value=<value>&token=terminology.api
        -> <value> = split_value 對應嘅值（有 terminology_id = 有權）

        2026-10-28b：同時寫 permit.db（permit = subject × permit × object 權威）
            subject   = value.split_value.<id>（split_value 類型）
            permit    = call
            object    = terminology.<terminology_id>
        """
        # 1. 本地 terminology 表（保留記錄）
        cur = self.conn.execute(
            "INSERT INTO terminology (terminology_id, split_value_id)"
            " SELECT ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM terminology"
            "  WHERE terminology_id = ? AND split_value_id = ?)",
            (terminology_id, split_value_id,
             terminology_id, split_value_id))
        # 2. permit.db（權威授權）
        try:
            from permit import Permit
            pm = Permit()
            try:
                pm.add_permit(
                    f"value.split_value.{split_value_id}", "split_value",
                    "call",
                    f"terminology.{terminology_id}", "terminology")
            finally:
                pm.close()
        except Exception as e:
            print(f"[value] permit.db 寫入失敗（本地表照寫）: {e}")
        self.conn.commit()
        if cur.rowcount:
            return cur.lastrowid
        r = self.conn.execute(
            "SELECT id FROM terminology"
            " WHERE terminology_id = ? AND split_value_id = ?",
            (terminology_id, split_value_id)).fetchone()
        return r["id"] if r else None

    def terminology_rows(self, split_value_id=None, active_only=True):
        """列出授權（可按拆分值篩選）"""
        sql = ("SELECT t.*, sv.split_value"
               " FROM terminology t"
               " LEFT JOIN split_value sv ON sv.id = t.split_value_id"
               " WHERE 1=1")
        args = []
        if split_value_id is not None:
            sql += " AND t.split_value_id = ?"
            args.append(split_value_id)
        if active_only:
            sql += " AND t.is_active = 1"
        sql += " ORDER BY t.id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def can_call_terminology(self, split_value_id, terminology_id):
        """一個拆分值有冇權 call terminology（冪等檢查）

        2026-10-28b：permit.db 係權威（subject × permit × object）；
        本地表 fallback（permit 未寫入時用本地記錄）。
        """
        try:
            from permit import Permit
            pm = Permit()
            try:
                ok = pm.can(
                    f"value.split_value.{split_value_id}", "split_value",
                    "call",
                    f"terminology.{terminology_id}", "terminology")
                if ok:
                    return True
            finally:
                pm.close()
        except Exception:
            pass
        # fallback：本地 terminology 表
        r = self.conn.execute(
            "SELECT 1 FROM terminology"
            " WHERE split_value_id = ? AND terminology_id = ?"
            " AND is_active = 1", (split_value_id, terminology_id)).fetchone()
        return r is not None

    def count(self):
        return self.conn.execute("SELECT COUNT(*) c FROM value").fetchone()["c"]

    def close(self):
        self.conn.close()