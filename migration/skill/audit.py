"""audit.py — migrate_audit 技能（2026-10-29 用戶要求）

module : migration > package : skill > audit.py

migrate_audit flow 嘅 3 步（value / run / evidence）—— 判斷由
terminology flow 引擎處理（_auto_answers），呢度提供 audit 專屬真檢查：
    check_value    = value.db 有冇呢個值（value_id 真查）
    check_run      = terminology.run 有冇呢個 run_id（真查）
    check_evidence = terminology.evidence 有冇呢個 value 嘅證據（真查）

每個 function 都係真 SQL（SELECT），零 hardcode：
    value_id = value.db value.id
    run_id   = terminology.run.id

用法：
    from migration.skill.audit import AuditSkill
    s = AuditSkill()
    s.check_value(123)
    s.check_run(456)
    s.check_evidence(123)
    s.close()
"""

import os
import sqlite3

META = r"C:\projects\meta"


class AuditSkill:
    """migrate_audit 技能：3 個真檢查（表話事，零 hardcode）"""

    def __init__(self, db_path=None):
        self.conn = sqlite3.connect(
            db_path or os.path.join(META, "migration", "migration.db"))
        self.conn.row_factory = sqlite3.Row

    def check_value(self, value_id):
        """真實 check value：value.db 有冇呢個 value_id"""
        try:
            c = sqlite3.connect(os.path.join(META, "value", "value.db"))
            try:
                c.row_factory = sqlite3.Row
                r = c.execute(
                    "SELECT id, value FROM value WHERE id = ?",
                    (value_id,)).fetchone()
                return {"value_id": value_id, "exists": r is not None,
                        "value": r["value"] if r else None}
            finally:
                c.close()
        except Exception:
            return {"value_id": value_id, "exists": False, "value": None}

    def check_run(self, run_id):
        """真實 check run：terminology.run 有冇呢個 run_id"""
        try:
            c = sqlite3.connect(os.path.join(META, "terminology",
                                             "terminology.db"))
            try:
                c.row_factory = sqlite3.Row
                r = c.execute(
                    "SELECT id, status_id FROM run WHERE id = ?",
                    (run_id,)).fetchone()
                return {"run_id": run_id, "exists": r is not None,
                        "status_id": r["status_id"] if r else None}
            finally:
                c.close()
        except Exception:
            return {"run_id": run_id, "exists": False, "status_id": None}

    def check_evidence(self, value_id):
        """真實 check evidence：terminology.evidence 有冇呢個 value 嘅證據"""
        try:
            c = sqlite3.connect(os.path.join(META, "terminology",
                                             "terminology.db"))
            try:
                c.row_factory = sqlite3.Row
                r = c.execute(
                    "SELECT COUNT(*) n FROM evidence WHERE value_id = ?"
                    " AND is_active = 1", (value_id,)).fetchone()
                n = r["n"] if r else 0
                return {"value_id": value_id, "exists": n > 0,
                        "evidence_count": n}
            finally:
                c.close()
        except Exception:
            return {"value_id": value_id, "exists": False,
                    "evidence_count": 0}

    def close(self):
        self.conn.close()