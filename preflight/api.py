"""api.py — preflight.db 對外 API

preflight = 起飛前檢查：plan 之前要過 preflight 檢查（系統 ready 先可以 plan）

2026-10-27（用戶要求）：
    preflight 表同 schema 好相似（都係 run_id 主導 + 資源引用）
    分別係時機：
        preflight = before plan（全局：成個系統 ready 未？）
        schema    = before execution（局部：呢個 job 要嘅嘢 ready 未？）

    add_registry(run_id, plan_id, skill_id, ...)  登記一次 preflight 檢查
    registries(run_id, plan_id, skill_id)         列出檢查
    check_preflight(run_id, plan_id, skill_id)    檢查 + 登記（run_id 由 terminology flow 產生）

用法：
    from preflight import Preflight
    s = Preflight()
    s.add_registry(run_id=1, plan_id=2, skill_id=3)
    s.close()
"""

import sqlite3

from .sql import SqlStore


class Preflight:
    """起飛前檢查（preflight.db）嘅對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def add_registry(self, run_id, plan_id=None, skill_id=None,
                     resource_formula_id=None, resource_structure_id=None):
        """登記一次 preflight 檢查（冪等：run_id 唯一）

        run_id = terminology.run.id（全站 flow 引擎產生）
        plan_id = sweep.target.id（可選；preflight 喺 plan 之前）
        """
        return self.store.add_registry(run_id, plan_id, skill_id,
                                       resource_formula_id,
                                       resource_structure_id)

    def registries(self, run_id=None, plan_id=None, skill_id=None,
                   active_only=True, limit=100):
        """列出 preflight 檢查（可按 run / plan / skill 篩選）"""
        return self.store.registries(run_id, plan_id, skill_id,
                                     active_only, limit)

    def check_preflight(self, run_id, plan_id=None, skill_id=None):
        """檢查 + 登記（run_id 由 terminology flow 產生）

        檢查（全局 readiness，全部要 ready 先算通過）：
            module_registry   = taxonomy.db 有冇 module 註冊
            structure_db      = structure.db 有冇真表
            rest_api_READ     = monitor.db 有冇 READ API
            rest_api_WRITE    = rule.db 有冇 WRITE rule
            value_db          = value.db 有冇值資產

        返回 {"ready": bool, "checks": [...], "registry_id": n}
        """
        checks = []

        # 1. module_registry（taxonomy.db）
        try:
            import sqlite3 as _sq
            _c = _sq.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
            _c.row_factory = _sq.Row
            try:
                n = _c.execute(
                    "SELECT COUNT(*) c FROM registry"
                    " WHERE tree_id = 2 AND is_active = 1").fetchone()["c"]
                checks.append({
                    "name": "module_registry", "type": "taxonomy",
                    "passed": n > 0,
                    "detail": f"{n} 個 module 已註冊" if n else "冇 module 註冊"})
            finally:
                _c.close()
        except Exception as exc:
            checks.append({
                "name": "module_registry", "type": "taxonomy",
                "passed": False, "detail": f"查唔到：{exc}"})

        # 2. structure_db（structure.db）
        try:
            import sqlite3 as _sq
            _c = _sq.connect(r"C:\projects\meta\structure\structure.db")
            _c.row_factory = _sq.Row
            try:
                n = _c.execute(
                    "SELECT COUNT(*) c FROM structure_db_table"
                    " WHERE is_active = 1").fetchone()["c"]
                checks.append({
                    "name": "structure_db", "type": "structure",
                    "passed": n > 0,
                    "detail": f"{n} 張真表已註冊" if n else "冇真表註冊"})
            finally:
                _c.close()
        except Exception as exc:
            checks.append({
                "name": "structure_db", "type": "structure",
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

        # 5. value_db（value.db）
        try:
            import sqlite3 as _sq
            _c = _sq.connect(r"C:\projects\meta\value\value.db")
            _c.row_factory = _sq.Row
            try:
                n = _c.execute(
                    "SELECT COUNT(*) c FROM value"
                    " WHERE is_active = 1").fetchone()["c"]
                checks.append({
                    "name": "value_db", "type": "value",
                    "passed": n > 0,
                    "detail": f"{n} 個值資產 ready" if n else "冇值資產"})
            finally:
                _c.close()
        except Exception as exc:
            checks.append({
                "name": "value_db", "type": "value",
                "passed": False, "detail": f"查唔到：{exc}"})

        all_ok = all(c["passed"] for c in checks)
        checks.append({
            "name": "preflight_ready", "type": "preflight_ready",
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