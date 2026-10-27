"""sql.py — identity.db 存取層（身份層：名字 → id 對應）"""

import sqlite3

from .function import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\identity\identity.db"

# 支援嘅身份類型（kind）
# identity 表：kind + name 唯一（package / flow / step / skill / module / resource / db）
KINDS = ["package", "flow", "step", "skill", "module", "resource", "db"]




class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS registry (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                kind       TEXT NOT NULL,             -- package / skill / flow / step ...
                name       TEXT NOT NULL,             -- 個名（例如 codegen / create_table）
                ref_id     INTEGER,                   -- 對應返來源系統嘅 id（例如 system.skill.id）
                taxonomy_id INTEGER,                  -- taxonomy.db taxonomy.id（分類）
                resource_id INTEGER,                  -- resource.db resource.id（資源）
                description TEXT,
                is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                UNIQUE (kind, name)
            )
        """)
        self.conn.commit()

    # ---------- 登記 ----------
    def register(self, kind, name, ref_id=None, description=None,
                 taxonomy_id=None, resource_id=None):
        """登記一個身份（冪等：已存在就更新 ref_id/description）

        2026-10-23：加 taxonomy_id / resource_id 選填欄位
        """
        if kind not in KINDS:
            raise ValueError(f"唔知嘅 kind: {kind}。可用：{KINDS}")
        self.conn.execute(
            """INSERT INTO registry (kind, name, ref_id, description,
                                     taxonomy_id, resource_id)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(kind, name) DO UPDATE SET
                   ref_id = COALESCE(excluded.ref_id, registry.ref_id),
                   description = COALESCE(excluded.description, registry.description),
                   taxonomy_id = COALESCE(excluded.taxonomy_id, registry.taxonomy_id),
                   resource_id = COALESCE(excluded.resource_id, registry.resource_id),
                   is_active = 1""",
            (kind, name, ref_id, description, taxonomy_id, resource_id))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM registry WHERE kind = ? AND name = ?", (kind, name)).fetchone()
        return r["id"] if r else None

    # ---------- 查詢 ----------
    def lookup(self, kind, name):
        """按 kind + name 查 id"""
        return self.conn.execute(
            "SELECT * FROM registry WHERE kind = ? AND name = ? AND is_active = 1",
            (kind, name)).fetchone()

    def lookup_all(self, kind=None):
        """列出全部身份（可按 kind 篩選）"""
        sql = "SELECT * FROM registry WHERE 1=1"
        args = ()
        if kind:
            sql += " AND kind = ?"
            args = (kind,)
        sql += " ORDER BY kind, name"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def resolve(self, kind, name_or_id):
        """由名或 id 攞身份

        name_or_id 係 int -> 按 id 查
        name_or_id 係 str -> 按 kind + name 查
        """
        if isinstance(name_or_id, int):
            return self.conn.execute(
                "SELECT * FROM registry WHERE id = ? AND is_active = 1", (name_or_id,)).fetchone()
        return self.lookup(kind, name_or_id)

    def kinds(self):
        """列出所有已用嘅 kind"""
        return [r["kind"] for r in self.conn.execute(
            "SELECT DISTINCT kind FROM registry ORDER BY kind")]

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()
