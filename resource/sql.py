"""sql.py — resource.db 存取層

resource = 資源層：記錄「邊個 module 用邊個 schema / tool」（by_id，2026-10-28
          用戶設計：trace 100% —— 唔可以有 ALL 偽抽象，逐個 id 記錄）

表：
    resource_schema  id | taxonomy.tree_id | schema.db registry.id
    resource_tool    id | taxonomy.tree_id | tool.db registry.id
    （registry / resource_taxonomy / resource_structure / resource_formula 保留）

冪等：INSERT ... WHERE NOT EXISTS（唔燒 sqlite_sequence）。
"""

import sqlite3

from . import schema as _schema

DB_PATH = r"C:\projects\meta\resource\resource.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        try:
            # 2026-10-28：resource_tool 舊版 tool_registry_id NOT NULL
            # -> 新版允許 NULL（「未用 tool」誠實狀態）。drop 重建（空表）。
            cols = {c[1] for c in self.conn.execute(
                "PRAGMA table_info('resource_tool')")} if self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table'"
                " AND name='resource_tool'").fetchone() else set()
            if cols and "tool_registry_id" in cols:
                nn = {c[1]: c[3] for c in self.conn.execute(
                    "PRAGMA table_info('resource_tool')")}
                if nn.get("tool_registry_id") == 1:
                    # 舊版 NOT NULL（notnull=1）-> drop 重建（呢張表啱啱
                    # 先建，冇歷史資料）
                    self.conn.execute("DROP TABLE resource_tool")
                    self.conn.commit()
                    print("[resource] resource_tool 重建（tool_registry_id"
                          " 允許 NULL）")
            for name in _schema.__all__:
                ddl = getattr(_schema, name)
                if isinstance(ddl, str):
                    self.conn.execute(ddl)
            for type_id, type_name in _schema.DEFAULT_TYPES:
                self.conn.execute(
                    'INSERT OR IGNORE INTO "type" (id, type) VALUES (?, ?)',
                    (type_id, type_name),
                )
            self.conn.commit()
        except Exception:
            self.conn.close()
            raise

    # ---------- resource_schema（2026-10-28 用戶設計） ----------
    def add_resource_schema(self, taxonomy_tree_id, schema_registry_id):
        """登記「module 用 schema」一次使用（冪等）

        taxonomy_tree_id    = taxonomy.tree.id（channel / module / skill）
        schema_registry_id  = schema.db registry.id
        """
        cur = self.conn.execute(
            "INSERT INTO resource_schema (taxonomy_tree_id, schema_registry_id)"
            " SELECT ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM resource_schema"
            "  WHERE taxonomy_tree_id = ? AND schema_registry_id = ?)",
            (taxonomy_tree_id, schema_registry_id,
             taxonomy_tree_id, schema_registry_id))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM resource_schema"
            " WHERE taxonomy_tree_id = ? AND schema_registry_id = ?",
            (taxonomy_tree_id, schema_registry_id)).fetchone()
        return r["id"] if r else (cur.lastrowid if cur.rowcount else None)

    def resource_schemas(self, taxonomy_tree_id=None, schema_registry_id=None,
                         active_only=True):
        """列出 resource_schema（可按 tree / schema registry 篩選）"""
        sql = "SELECT * FROM resource_schema WHERE 1=1"
        args = []
        if taxonomy_tree_id is not None:
            sql += " AND taxonomy_tree_id = ?"
            args.append(taxonomy_tree_id)
        if schema_registry_id is not None:
            sql += " AND schema_registry_id = ?"
            args.append(schema_registry_id)
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    # ---------- resource_tool（2026-10-28 用戶設計） ----------
    def add_resource_tool(self, taxonomy_tree_id, tool_registry_id=None):
        """登記「module 用 tool」一次使用（冪等）

        taxonomy_tree_id  = taxonomy.tree.id（channel / module / skill）
        tool_registry_id  = tool.db registry.id（None = 未用任何 tool）
        """
        cur = self.conn.execute(
            "INSERT INTO resource_tool (taxonomy_tree_id, tool_registry_id)"
            " SELECT ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM resource_tool"
            "  WHERE taxonomy_tree_id = ?"
            "    AND coalesce(tool_registry_id, -1) = coalesce(?, -1))",
            (taxonomy_tree_id, tool_registry_id,
             taxonomy_tree_id, tool_registry_id))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM resource_tool"
            " WHERE taxonomy_tree_id = ?"
            "   AND coalesce(tool_registry_id, -1) = coalesce(?, -1)",
            (taxonomy_tree_id, tool_registry_id)).fetchone()
        return r["id"] if r else (cur.lastrowid if cur.rowcount else None)

    def resource_tools(self, taxonomy_tree_id=None, tool_registry_id=None,
                       active_only=True):
        """列出 resource_tool（可按 tree / tool registry 篩選）"""
        sql = "SELECT * FROM resource_tool WHERE 1=1"
        args = []
        if taxonomy_tree_id is not None:
            sql += " AND taxonomy_tree_id = ?"
            args.append(taxonomy_tree_id)
        if tool_registry_id is not None:
            sql += " AND tool_registry_id = ?"
            args.append(tool_registry_id)
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def close(self):
        self.conn.close()


__all__ = ["DB_PATH", "SqlStore"]
