"""api.py — migration.db 對外 API（遷移審計日誌）"""

from .sql import SqlStore


class Migration:
    """migration_log 嘅對外介面

    用法：
        from migration import Migration
        m = Migration()
        m.record("source", table="api", migration_type="schema",
                 description="api 加 proven 欄")
        m.logs("source")
    """

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def record(self, module_name, table=None, migration_type="schema",
               description=None, run_id=None, api_id=None, row_id=0,
               value=None, value_id=None, step_values=None, run_flow=True):
        """記錄一次 migration（冪等）

        value = 提交值（跑 terminology flow；冇 -> description 做值）
        value_id = 已存在 value.id（重用，優先於 value）
        run_flow = False 就唔跑 flow（內部用）
        """
        return self.store.record(
            module_name, table, migration_type, description,
            run_id, api_id, row_id, value, value_id, step_values, run_flow)

    def logs(self, module_name=None, migration_type=None, limit=100):
        """列出 migration 記錄"""
        return self.store.logs(module_name, migration_type, limit)

    def stats(self):
        """統計：總數 + by module/type"""
        return {"total": self.store.count(),
                "by_module": self.store.by_module()}

    def close(self):
        self.store.close()
