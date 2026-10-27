"""sql.py — schema.db 存取層

schema = 環境檢查層：mission 之前要過 schema 檢查（環境 ready 先可以做 mission）

    schema_check 表 = 每次檢查記錄（task_id | check_name | check_type | passed | detail）
    schema_run   表 = 每次 schema 執行（task_id | total | passed | failed | status）

檢查類型（check_type）：
    api_exists     = 要 call N 個 site，有冇 N 個 api？（registry type_id=4）
    value_active   = value 係咪 active？（registry type_id=11 is_active=1）
    value_broken   = value 會唔會 broken？（有冇對應 db_field / lineage）
    value_missing  = value 係咪 missing？（要 build + proof 先可以做 mission）

用法：
    from schema.sql import SqlStore
    s = SqlStore()
    s.add_check(task_id=1, check_name="api_exists", check_type="api_exists",
                passed=1, detail="10/10 api 存在")
    s.close()
"""

import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\schema\schema.db"




class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(SCHEMA_CHECK_DDL)
        self.conn.execute(SCHEMA_RUN_DDL)
        self.conn.commit()

    # ---------- schema_check ----------
    def add_check(self, task_id, check_name, check_type, passed, detail=None):
        cur = self.conn.execute(
            "INSERT INTO schema_check (task_id, check_name, check_type, passed, detail)"
            " VALUES (?, ?, ?, ?, ?)",
            (task_id, check_name, check_type, 1 if passed else 0, detail))
        self.conn.commit()
        return cur.lastrowid

    def checks(self, task_id=None, limit=100):
        sql = "SELECT * FROM schema_check WHERE is_active = 1"
        params = []
        if task_id is not None:
            sql += " AND task_id = ?"
            params.append(task_id)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in self.conn.execute(sql, params)]

    # ---------- schema_run ----------
    def add_run(self, task_id, total, passed, failed):
        status = "ready" if failed == 0 else "not_ready"
        cur = self.conn.execute(
            "INSERT INTO schema_run (task_id, total, passed, failed, status)"
            " VALUES (?, ?, ?, ?, ?)",
            (task_id, total, passed, failed, status))
        self.conn.commit()
        return cur.lastrowid

    def runs(self, task_id=None, limit=20):
        sql = "SELECT * FROM schema_run"
        params = []
        if task_id is not None:
            sql += " WHERE task_id = ?"
            params.append(task_id)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in self.conn.execute(sql, params)]

    def count(self):
        return self.conn.execute(
            "SELECT COUNT(*) FROM schema_check WHERE is_active = 1").fetchone()[0]

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()