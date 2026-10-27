# registry.py — terminology package 嘅名稱註冊表（SSOT）
# 術語值與 skill flow 嘅關聯註冊

import sqlite3

from .schema import REGISTRY_DDL

DB_PATH = "C:/projects/meta/terminology/terminology.db"


class RegistryStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        cols = {r[1] for r in self.conn.execute(
            "PRAGMA table_info('registry')")}
        expected = {"id", "value_id", "modele_skill_id", "flow_pass_id"}
        if cols and cols != expected:
            count = self.conn.execute(
                "SELECT COUNT(*) FROM registry").fetchone()[0]
            if count:
                self.conn.close()
                raise ValueError(
                    "舊 registry 有資料，無法自動轉成 value_id/"
                    "modele_skill_id/flow_pass_id；請先手動遷移")
            self.conn.execute("DROP TABLE registry")
        self.conn.execute(REGISTRY_DDL)
        self.conn.commit()

    def list_registry(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM registry ORDER BY id")]

    def register(self, value_id, modele_skill_id, flow_pass_id):
        """登記術語值嘅 skill flow 關聯（冪等）"""
        self.conn.execute(
            "INSERT INTO registry (value_id, modele_skill_id, flow_pass_id)"
            " SELECT ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM registry WHERE value_id = ?"
            "  AND modele_skill_id = ? AND flow_pass_id = ?)",
            (value_id, modele_skill_id, flow_pass_id,
             value_id, modele_skill_id, flow_pass_id))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM registry WHERE value_id = ?"
            " AND modele_skill_id = ? AND flow_pass_id = ?",
            (value_id, modele_skill_id, flow_pass_id)).fetchone()
        return r["id"] if r else None

    def close(self):
        self.conn.close()
