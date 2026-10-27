"""sql.py — option.db 存取層"""

import sqlite3

import option.schema as _schema

DB_PATH = r"C:\projects\meta\option\option.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        try:
            for ddl in _schema.__all__:
                self.conn.execute(getattr(_schema, ddl))
            self._migrate()
            self.conn.commit()
        except Exception:
            self.conn.close()
            raise

    def _migrate(self):
        """遷移（幂等）：table_field_option 升級（2026-10-25）

        1. 加 structure_db_field_id / structure_db_table_id 欄
        2. 舊版 resource_id NOT NULL -> 新版可 NULL（重建表保留資料）
        """
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('table_field_option')")]
        info = {x[1]: x for x in self.conn.execute(
            "PRAGMA table_info('table_field_option')")}
        need = {"structure_db_field_id", "structure_db_table_id"}
        old_notnull = info.get("resource_id") and info["resource_id"][3] == 1
        if not (need <= set(cols)) or old_notnull:
            # 舊表 -> 重建（保留資料；resource_id 改可 NULL）
            rows = [dict(r) for r in self.conn.execute(
                "SELECT * FROM table_field_option")]
            self.conn.execute("DROP TABLE table_field_option")
            self.conn.execute(_schema.DB_FIELD_OPTION_DDL)
            for r in rows:
                self.conn.execute(
                    "INSERT INTO table_field_option"
                    " (id, resource_id, structure_db_field_id,"
                    "  structure_db_table_id, value, description,"
                    "  is_active, created_at, updated_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (r["id"], r.get("resource_id"),
                     r.get("structure_db_field_id"),
                     r.get("structure_db_table_id"),
                     r["value"], r.get("description"),
                     r.get("is_active", 1),
                     r.get("created_at"), r.get("updated_at")))
            print("[option] table_field_option 重建"
                  "（+ structure ids；resource_id 可 NULL）")
        return

    def options(self, resource_id=None, structure_db_field_id=None,
                active_only=True):
        """一個資源 / 欄位嘅允許值清單"""
        sql = "SELECT * FROM table_field_option WHERE 1=1"
        args = []
        if resource_id is not None:
            sql += " AND resource_id = ?"
            args.append(resource_id)
        if structure_db_field_id is not None:
            sql += " AND structure_db_field_id = ?"
            args.append(structure_db_field_id)
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def add_option(self, resource_id=None, value=None, description=None,
                   structure_db_field_id=None, structure_db_table_id=None):
        """加一個允許值（冪等；resource_id 或 structure_db_field_id 至少一個）"""
        if value is None:
            raise ValueError("value 唔可以空")
        if resource_id is None and structure_db_field_id is None:
            raise ValueError("resource_id 或 structure_db_field_id 至少一個")
        self.conn.execute(
            "INSERT INTO table_field_option"
            " (resource_id, structure_db_field_id, structure_db_table_id,"
            "  value, description, updated_at)"
            " SELECT ?, ?, ?, ?, ?, datetime('now', 'localtime')"
            " WHERE NOT EXISTS"
            " (SELECT 1 FROM table_field_option"
            "  WHERE coalesce(resource_id, -1) = coalesce(?, -1)"
            "    AND coalesce(structure_db_field_id, -1) = coalesce(?, -1)"
            "    AND value = ?)",
            (resource_id, structure_db_field_id, structure_db_table_id,
             value, description,
             resource_id, structure_db_field_id, value))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM table_field_option WHERE value = ?"
            " AND coalesce(resource_id, -1) = coalesce(?, -1)"
            " AND coalesce(structure_db_field_id, -1) = coalesce(?, -1)"
            " ORDER BY id DESC LIMIT 1",
            (value, resource_id, structure_db_field_id)).fetchone()
        return r["id"] if r else None

    def has_option(self, resource_id=None, value=None,
                   structure_db_field_id=None, active_only=True):
        """呢個值喺唔喺允許清單"""
        sql = ("SELECT 1 FROM table_field_option"
               " WHERE value = ?"
               " AND coalesce(resource_id, -1) = coalesce(?, -1)"
               " AND coalesce(structure_db_field_id, -1) = coalesce(?, -1)")
        args = [value, resource_id, structure_db_field_id]
        if active_only:
            sql += " AND is_active = 1"
        return self.conn.execute(sql, args).fetchone() is not None

    def remove_option(self, resource_id=None, value=None,
                      structure_db_field_id=None):
        self.conn.execute(
            "DELETE FROM table_field_option"
            " WHERE value = ?"
            " AND coalesce(resource_id, -1) = coalesce(?, -1)"
            " AND coalesce(structure_db_field_id, -1) = coalesce(?, -1)",
            (value, resource_id, structure_db_field_id))
        self.conn.commit()

    def all_options(self, active_only=True):
        """全部允許值（唔篩選）"""
        sql = "SELECT * FROM table_field_option"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def reset(self):
        """reset：清空全部 option（重新開始）"""
        self.conn.execute("DELETE FROM table_field_option")
        self.conn.commit()

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()