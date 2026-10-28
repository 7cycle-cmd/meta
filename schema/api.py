"""api.py — schema.db 對外 API

schema = 環境檢查層：mission 之前要過 schema 檢查（環境 ready 先可以做 mission）

2026-10-27（用戶要求 redesign）：
    schema_check / schema_run 表已移除（drop）
    -> 新 registry 表：run_id 由 terminology 產生（全站 flow 引擎）

    add_registry(run_id, plan_id, skill_id, ...)  登記一次 schema 檢查
    registries(run_id, plan_id, skill_id)         列出檢查
    check_schema(run_id, plan_id, skill_id)       檢查 + 登記（run_id 由 terminology flow 產生）

用法：
    from schema import Schema
    s = Schema()
    s.add_registry(run_id=1, plan_id=2, skill_id=3)
    s.close()
"""

import sqlite3

from .sql import SqlStore

RESOURCE_DB = r"C:\projects\meta\resource\resource.db"


class Schema:
    """環境檢查層（schema.db）嘅對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def add_registry(self, run_id, plan_id=None, skill_id=None,
                     resource_formula_id=None, resource_structure_id=None):
        """登記一次 schema 檢查（冪等：run_id 唯一）

        run_id = terminology.run.id（全站 flow 引擎產生）
        plan_id = sweep.target.id（value_id + condition_id 喺 run_id）
        """
        return self.store.add_registry(run_id, plan_id, skill_id,
                                       resource_formula_id,
                                       resource_structure_id)

    def registries(self, run_id=None, plan_id=None, skill_id=None,
                   active_only=True, limit=100):
        """列出 schema 檢查（可按 run / plan / skill 篩選）"""
        return self.store.registries(run_id, plan_id, skill_id,
                                     active_only, limit)

    def check_schema(self, run_id, plan_id=None, skill_id=None):
        """檢查 + 登記（run_id 由 terminology flow 產生）

        檢查（全部要 ready 先算通過）：
            structure_db_table  = structure.db 有冇呢張表（table 存在）
            structure_db_field  = structure.db 有冇呢個欄位（ABC=1 ready condition）
            rest_api_READ       = monitor.db 有冇呢個 READ API（READ ready）
            rest_api_WRITE      = rule.db 有冇呢個 WRITE API（WRITE ready）

        返回 {"ready": bool, "checks": [...], "registry_id": n}
        """
        checks = []

        # 1. structure_db_table（table 存在）
        try:
            import sqlite3 as _sq
            _c = _sq.connect(r"C:\projects\meta\structure\structure.db")
            _c.row_factory = _sq.Row
            try:
                n = _c.execute(
                    "SELECT COUNT(*) c FROM structure_db_table"
                    " WHERE is_active = 1").fetchone()["c"]
                checks.append({
                    "name": "structure_db_table", "type": "structure",
                    "passed": n > 0,
                    "detail": f"{n} 張真表已註冊" if n else "冇真表註冊"})
            finally:
                _c.close()
        except Exception as exc:
            checks.append({
                "name": "structure_db_table", "type": "structure",
                "passed": False, "detail": f"查唔到：{exc}"})

        # 2. structure_db_field（ABC=1 ready condition）
        try:
            import sqlite3 as _sq
            _c = _sq.connect(r"C:\projects\meta\structure\structure.db")
            _c.row_factory = _sq.Row
            try:
                n = _c.execute(
                    "SELECT COUNT(*) c FROM structure_db_field"
                    " WHERE is_active = 1").fetchone()["c"]
                checks.append({
                    "name": "structure_db_field", "type": "structure",
                    "passed": n > 0,
                    "detail": f"{n} 個真欄位已註冊" if n else "冇欄位註冊"})
            finally:
                _c.close()
        except Exception as exc:
            checks.append({
                "name": "structure_db_field", "type": "structure",
                "passed": False, "detail": f"查唔到：{exc}"})

        # 3. rest_api_READ（monitor.db）
        try:
            import sqlite3 as _sq
            _c = _sq.connect(r"C:\projects\meta\monitor\monitor.db")
            _c.row_factory = _sq.Row
            try:
                n = _c.execute(
                    "SELECT COUNT(*) c FROM rest_api_READ"
                    " WHERE is_active = 1").fetchone()["c"]
                checks.append({
                    "name": "rest_api_READ", "type": "rest_api",
                    "passed": n > 0,
                    "detail": f"{n} 個 READ API ready" if n else "冇 READ API"})
            finally:
                _c.close()
        except Exception as exc:
            checks.append({
                "name": "rest_api_READ", "type": "rest_api",
                "passed": False, "detail": f"查唔到：{exc}"})

        # 4. rest_api_WRITE（tool.db，WRITE 中心）
        try:
            import sqlite3 as _sq
            _c = _sq.connect(r"C:\projects\meta\tool\tool.db")
            _c.row_factory = _sq.Row
            try:
                n = _c.execute(
                    "SELECT COUNT(*) c FROM rest_api_WRITE"
                    " WHERE is_active = 1").fetchone()["c"]
                checks.append({
                    "name": "rest_api_WRITE", "type": "rest_api",
                    "passed": n > 0,
                    "detail": f"{n} 個 WRITE API ready" if n else "冇 WRITE API"})
            finally:
                _c.close()
        except Exception as exc:
            checks.append({
                "name": "rest_api_WRITE", "type": "rest_api",
                "passed": False, "detail": f"查唔到：{exc}"})

        all_ok = all(c["passed"] for c in checks)
        checks.append({
            "name": "schema_ready", "type": "schema_ready",
            "passed": all_ok,
            "detail": "全部 ready" if all_ok else "有嘢未 ready"})

        # 登記（run_id 由 terminology flow 產生）
        registry_id = self.store.add_registry(run_id, plan_id, skill_id)
        self.store.commit()

        return {"ready": all_ok, "checks": checks,
                "registry_id": registry_id, "run_id": run_id}

    def count(self):
        return self.store.count()

    def close(self):
        self.store.close()