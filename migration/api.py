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

    def check_column(self, module_name, table, column):
        """真實檢查：column 存唔存在（PRAGMA table_info 權威）

        module_name = taxonomy.registry.meta（邊個 module；決定 db 檔）
        table       = 張表名
        column      = 欄位名

        返回 {"exists": bool, "db_file": str, "table": str, "column": str}
        """
        return self.store.check_column(module_name, table, column)

    def add_column(self, module_name, table, column, column_type="TEXT"):
        """真實加欄位（ALTER TABLE ADD COLUMN；冪等）

        返回 {"added": bool, "already": bool, "exists": bool, ...}
        """
        return self.store.add_column(module_name, table, column,
                                     column_type)

    def close(self):
        self.store.close()
