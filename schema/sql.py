"""sql.py — schema.db 存取層

schema = 環境檢查層：mission 之前要過 schema 檢查（環境 ready 先可以做 mission）

2026-10-27（用戶要求 redesign）：
    schema_check / schema_run 表已移除（drop）
    -> 新 registry 表：run_id 由 terminology 產生（全站 flow 引擎）

registry 表：
    run_id                 = terminology.run.id（flow 產生）
    plan_id                = sweep.target.id（value_id + condition_id 喺 run_id）
    skill_id               = skill.id
    resource_formula_id    = 資源 formula（未註冊）
    resource_structure_id  = 資源 structure（未註冊）

用法：
    from schema.sql import SqlStore
    s = SqlStore()
    s.add_registry(run_id=1, plan_id=2, skill_id=3)
    s.close()
"""

import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\schema\schema.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._migrate_drop_old_tables()
        self.conn.execute(REGISTRY_DDL)
        # schema_registry（2026-10-28 用戶設計）：DDL 定義 by id
        self.conn.execute(SCHEMA_REGISTRY_DDL)
        self.conn.commit()

    def _migrate_drop_old_tables(self):
        """遷移（幂等）：drop 舊 schema_check / schema_run 表（2026-10-27）

        用戶要求：remove -> table : scheme_check and scheme_run
        另外：舊 registry 表（meta 字典，registry.py 建立）同新 registry
        表（run_id 設計）撞名 -> 舊表有 meta 欄 = 舊版，drop 重建。
        """
        for t in ("schema_check", "schema_run"):
            has = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (t,)).fetchone()
            if has:
                self.conn.execute(f"DROP TABLE {t}")
                self.conn.commit()
                print(f"[schema] drop 舊表 {t}")
        # 舊 registry（meta 字典）-> drop（新 registry 表 run_id 設計）
        has = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='registry'").fetchone()
        if has:
            cols = {c[1] for c in self.conn.execute(
                "PRAGMA table_info('registry')")}
            if "run_id" not in cols:
                self.conn.execute("DROP TABLE registry")
                self.conn.commit()
                print("[schema] drop 舊 registry 表（meta 字典）")

    # ---------- registry ----------
    def add_registry(self, run_id, plan_id=None, skill_id=None,
                     resource_formula_id=None, resource_structure_id=None):
        """登記一次 schema 檢查（冪等：run_id 唯一）

        run_id = terminology.run.id（全站 flow 引擎產生）
        """
        cur = self.conn.execute(
            "INSERT INTO registry"
            " (run_id, plan_id, skill_id, resource_formula_id,"
            "  resource_structure_id)"
            " SELECT ?, ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM registry WHERE run_id = ?)",
            (run_id, plan_id, skill_id, resource_formula_id,
             resource_structure_id, run_id))
        self.conn.commit()
        if cur.rowcount:
            return cur.lastrowid
        r = self.conn.execute(
            "SELECT id FROM registry WHERE run_id = ?", (run_id,)).fetchone()
        return r["id"] if r else None

    def registries(self, run_id=None, plan_id=None, skill_id=None,
                   active_only=True, limit=100):
        """列出 schema 檢查（可按 run / plan / skill 篩選）"""
        sql = "SELECT * FROM registry WHERE 1=1"
        args = []
        if run_id is not None:
            sql += " AND run_id = ?"
            args.append(run_id)
        if plan_id is not None:
            sql += " AND plan_id = ?"
            args.append(plan_id)
        if skill_id is not None:
            sql += " AND skill_id = ?"
            args.append(skill_id)
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        return [dict(r) for r in self.conn.execute(sql, args)]

    # ---------- schema_registry（2026-10-28 用戶設計：DDL 定義 by id） ----------
    def add_schema_registry(self, meta, source=None, description=None):
        """登記一個 schema 定義（冪等：meta UNIQUE）

        meta   = DDL symbol 名（e.g. REGISTRY_DDL / CONDITION_DDL）
        source = 定義來源（e.g. terminology/schema.py）
        """
        cur = self.conn.execute(
            "INSERT INTO schema_registry (meta, source, description)"
            " SELECT ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM schema_registry WHERE meta = ?)",
            (meta, source, description, meta))
        self.conn.commit()
        if cur.rowcount:
            return cur.lastrowid
        r = self.conn.execute(
            "SELECT id FROM schema_registry WHERE meta = ?", (meta,)).fetchone()
        return r["id"] if r else None

    def schema_registries(self, active_only=True):
        """列出 schema 定義（全部已登記 DDL symbol）"""
        sql = "SELECT * FROM schema_registry"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def count(self):
        return self.conn.execute(
            "SELECT COUNT(*) FROM registry WHERE is_active = 1").fetchone()[0]

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()