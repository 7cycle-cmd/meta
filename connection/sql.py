"""sql.py — connection.db 存取層（完整連接資料模型）

connection = 表之間嘅 FK 連接
    identity           角色字典（1=sender / 2=receiver）
    connection_registry 統一註冊表（identity_id | resource_id | is_active）
    connection         連接（id | sender_id | receiver_id | is_active）
    connection_quality 連接品質（id | connection_id | status_id | performance_ms）
    connection_status  連接狀態字典（pass / fail）

    is_active  = proof（記錄存唔存在）
    updated_at = 最後連接時間（last connection time）
"""

import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\connection\connection.db"


# 統一註冊表（sender + receiver 合一）





class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            IDENTITY_DDL + CONNECTION_REGISTRY_DDL + CONNECTION_DDL
            + CONNECTION_STATUS_DDL + CONNECTION_QUALITY_DDL)
        self.conn.commit()
        # 預填 identity（sender / receiver）
        for iid, meta, desc in [(1, "sender", "發送者（A 端）"),
                                (2, "receiver", "接收者（B 端）")]:
            self.conn.execute(
                "INSERT OR IGNORE INTO identity (id, meta, description)"
                " VALUES (?, ?, ?)", (iid, meta, desc))
        # 預填 connection_status（pass / fail）
        for meta, desc in [("pass", "連接成立"), ("fail", "連接唔成立")]:
            self.conn.execute(
                "INSERT OR IGNORE INTO connection_status (meta, description)"
                " VALUES (?, ?)", (meta, desc))
        self.conn.commit()

    # ---------- connection_registry（統一註冊表） ----------
    def upsert_registry(self, identity, resource_id, is_active=1):
        """建立/更新一個註冊（identity = sender / receiver）

        identity_id 自動由 identity 表解析。
        資源可以同時係 sender + receiver（兩個 identity 各一行）。
        """
        row = self.conn.execute(
            "SELECT id FROM identity WHERE meta = ?", (identity,)).fetchone()
        if not row:
            raise ValueError(f"identity 必須係 sender/receiver，收到：{identity}")
        iid = row["id"]
        r = self.conn.execute(
            "SELECT id FROM connection_registry"
            " WHERE identity_id = ? AND resource_id = ?",
            (iid, resource_id)).fetchone()
        if r:
            self.conn.execute(
                "UPDATE connection_registry SET is_active = ?,"
                " updated_at = datetime('now', 'localtime') WHERE id = ?",
                (is_active, r["id"]))
            self.conn.commit()
            return r["id"]
        cur = self.conn.execute(
            "INSERT INTO connection_registry (identity_id, resource_id, is_active)"
            " VALUES (?, ?, ?)", (iid, resource_id, is_active))
        self.conn.commit()
        return cur.lastrowid

    def registry_by_resource(self, resource_id):
        """按 resource_id 攞所有註冊（一個資源可以有多個角色）"""
        return [dict(r) for r in self.conn.execute(
            "SELECT cr.id, i.meta AS identity, cr.resource_id, cr.is_active"
            " FROM connection_registry cr"
            " JOIN identity i ON i.id = cr.identity_id"
            " WHERE cr.resource_id = ? ORDER BY cr.id", (resource_id,))]

    def registries(self, identity=None, active_only=True):
        """列出註冊（可按身份篩選）"""
        sql = """SELECT cr.id, i.meta AS identity, cr.resource_id, cr.is_active
                 FROM connection_registry cr
                 JOIN identity i ON i.id = cr.identity_id
                 WHERE 1=1"""
        args = ()
        if identity:
            sql += " AND i.meta = ?"
            args = (identity,)
        if active_only:
            sql += " AND cr.is_active = 1"
        sql += " ORDER BY cr.id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    # ---------- connection ----------
    def upsert_connection(self, sender_id, receiver_id, is_active=1):
        """建立 A -> B 連接（冪等）

        sender_id / receiver_id = connection_registry.id
        is_active = proof（連接存在）
        updated_at = 最後連接時間（自動更新）
        """
        r = self.conn.execute(
            "SELECT id FROM connection WHERE sender_id = ? AND receiver_id = ?",
            (sender_id, receiver_id)).fetchone()
        if r:
            self.conn.execute(
                "UPDATE connection SET is_active = ?, updated_at = datetime('now', 'localtime')"
                " WHERE id = ?", (is_active, r["id"]))
            self.conn.commit()
            return r["id"]
        cur = self.conn.execute(
            "INSERT INTO connection (sender_id, receiver_id, is_active) VALUES (?, ?, ?)",
            (sender_id, receiver_id, is_active))
        self.conn.commit()
        return cur.lastrowid

    def touch_connection(self, connection_id):
        """更新連接時間（每次使用 A <-> B 就 touch）"""
        self.conn.execute(
            "UPDATE connection SET updated_at = datetime('now', 'localtime')"
            " WHERE id = ?", (connection_id,))
        self.conn.commit()

    # ---------- connection_quality ----------
    def upsert_quality(self, connection_id, status, performance_ms=None, is_active=1):
        """記錄連接品質（pass / fail + 效能）

        is_active = proof（品質記錄存唔存在）
        """
        sid = self.conn.execute(
            "SELECT id FROM connection_status WHERE meta = ?", (status,)).fetchone()
        if not sid:
            raise ValueError(f"status 必須係 pass/fail，收到：{status}")
        r = self.conn.execute(
            "SELECT id FROM connection_quality WHERE connection_id = ?",
            (connection_id,)).fetchone()
        if r:
            self.conn.execute(
                "UPDATE connection_quality SET status_id = ?, performance_ms = ?,"
                " is_active = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                (sid["id"], performance_ms, is_active, r["id"]))
            self.conn.commit()
            return r["id"]
        cur = self.conn.execute(
            "INSERT INTO connection_quality (connection_id, status_id, is_active, performance_ms)"
            " VALUES (?, ?, ?, ?)",
            (connection_id, sid["id"], is_active, performance_ms))
        self.conn.commit()
        return cur.lastrowid

    # ---------- 查詢 ----------
    def connections(self, active_only=True):
        # ATTACH resource.db 攞資源名（connection_registry.resource_id = resource.db registry.id）
        # 2026-10-28：resource module 未重建（空殼）-> 冇 registry JOIN（sender/receiver 用 id）
        import os
        if not os.path.exists(r"C:\projects\meta\resource\resource.db"):
            sql = """SELECT c.id,
                            c.sender_id, NULL AS sender,
                            c.receiver_id, NULL AS receiver,
                            c.is_active, c.created_at, c.updated_at,
                            q.is_active AS quality_active, q.performance_ms,
                            cs.meta AS status
                     FROM connection c
                     JOIN connection_registry s ON s.id = c.sender_id
                     JOIN connection_registry r ON r.id = c.receiver_id
                     LEFT JOIN connection_quality q ON q.connection_id = c.id
                     LEFT JOIN connection_status cs ON cs.id = q.status_id
                     WHERE 1=1"""
            args = ()
            if active_only:
                sql += " AND c.is_active = 1"
            sql += " ORDER BY c.id"
            return [dict(r) for r in self.conn.execute(sql, args)]
        self.conn.execute(
            "ATTACH DATABASE ? AS resdb", (r"C:\projects\meta\resource\resource.db",))
        try:
            sql = """SELECT c.id,
                            c.sender_id, sr.meta AS sender,
                            c.receiver_id, rr.meta AS receiver,
                            c.is_active, c.created_at, c.updated_at,
                            q.is_active AS quality_active, q.performance_ms,
                            cs.meta AS status
                     FROM connection c
                     JOIN connection_registry s ON s.id = c.sender_id
                     JOIN connection_registry r ON r.id = c.receiver_id
                     LEFT JOIN resdb.registry sr ON sr.id = s.resource_id
                     LEFT JOIN resdb.registry rr ON rr.id = r.resource_id
                     LEFT JOIN connection_quality q ON q.connection_id = c.id
                     LEFT JOIN connection_status cs ON cs.id = q.status_id
                     WHERE 1=1"""
            args = ()
            if active_only:
                sql += " AND c.is_active = 1"
            sql += " ORDER BY c.id"
            return [dict(r) for r in self.conn.execute(sql, args)]
        finally:
            self.conn.execute("DETACH DATABASE resdb")

    def registries(self, identity=None, active_only=True):
        """列出註冊（identity = sender / receiver / None = 全部）"""
        sql = """SELECT cr.id, i.meta AS identity, cr.resource_id,
                        cr.is_active, cr.created_at, cr.updated_at
                 FROM connection_registry cr
                 JOIN identity i ON i.id = cr.identity_id
                 WHERE 1=1"""
        args = ()
        if identity:
            sql += " AND i.meta = ?"
            args = (identity,)
        if active_only:
            sql += " AND cr.is_active = 1"
        sql += " ORDER BY cr.id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    # ---------- table_group：表 × 欄位（sender=表，receiver=欄位） ----------
    def registry_connections_by_sender(self, sender_resource_id,
                                       active_only=True):
        """攞一個 sender（表）連去嘅 receiver（欄位）清單

        sender_resource_id = resource.db registry.id（type=db_table）
        返回每行：connection_id / receiver_resource_id / receiver_meta /
                  is_active
        """
        import os
        if not os.path.exists(r"C:\projects\meta\resource\resource.db"):
            # resource module 未重建（2026-10-28）-> 冇 receiver_meta
            return [dict(r) for r in self.conn.execute(
                """SELECT c.id AS connection_id,
                           r.resource_id AS receiver_resource_id,
                           NULL AS receiver_meta,
                           c.is_active
                    FROM connection c
                    JOIN connection_registry s ON s.id = c.sender_id
                    JOIN connection_registry r ON r.id = c.receiver_id
                    WHERE s.resource_id = ?"""
                + (" AND c.is_active = 1" if active_only else "")
                + " ORDER BY c.id", (sender_resource_id,))]
        self.conn.execute(
            "ATTACH DATABASE ? AS resdb", (r"C:\projects\meta\resource\resource.db",))
        try:
            sql = """SELECT c.id AS connection_id,
                            r.resource_id AS receiver_resource_id,
                            rr.meta AS receiver_meta,
                            c.is_active
                     FROM connection c
                     JOIN connection_registry s ON s.id = c.sender_id
                     JOIN connection_registry r ON r.id = c.receiver_id
                     LEFT JOIN resdb.registry rr ON rr.id = r.resource_id
                     WHERE s.resource_id = ?"""
            args = (sender_resource_id,)
            if active_only:
                sql += " AND c.is_active = 1"
            sql += " ORDER BY c.id"
            return [dict(r) for r in self.conn.execute(sql, args)]
        finally:
            self.conn.execute("DETACH DATABASE resdb")

    def identities(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM identity ORDER BY id")]

    def statuses(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM connection_status ORDER BY id")]

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()