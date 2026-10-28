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

    def inspect_table(self, module_name, table):
        """真實 inspect：PRAGMA table_info 攞欄位清單"""
        return self.store.inspect_table(module_name, table)

    def backfill_column(self, module_name, table, column):
        """真實回填：count 有值 row 數"""
        return self.store.backfill_column(module_name, table, column)

    def verify_column(self, module_name, table, column):
        """真實 verify：PRAGMA 確認欄位存在"""
        return self.store.verify_column(module_name, table, column)

    def verify_rowcount(self, module_name, table):
        """真實 verify rowcount：count(*)"""
        return self.store.verify_rowcount(module_name, table)

    def report(self, module_name=None, table=None):
        """真實 report：migration_log 統計"""
        return self.store.report(module_name, table)

    def check_dictionary(self, module_name, table):
        """真實 check dictionary：已有值清單"""
        return self.store.check_dictionary(module_name, table)

    def check_symbol(self, module_name, table, symbol, column="symbol"):
        """真實 check symbol：有冇呢個 symbol"""
        return self.store.check_symbol(module_name, table, symbol, column)

    def insert_symbol(self, module_name, table, symbol, description=None,
                      column="symbol"):
        """真實 insert symbol（冪等）"""
        return self.store.insert_symbol(module_name, table, symbol,
                                        description, column)

    def verify_symbol(self, module_name, table, symbol, column="symbol"):
        """真實 verify symbol：SELECT 確認存在"""
        return self.store.verify_symbol(module_name, table, symbol, column)

    def check_source(self, module_name, table=None):
        """真實 check source：source 表記錄數"""
        return self.store.check_source(module_name, table)

    def fetch_external(self, module_name, url, table="postman_sync"):
        """真實 fetch external：POST 記錄"""
        return self.store.fetch_external(module_name, url, table)

    def map_to_local(self, module_name, table, raw_json=None):
        """真實 map：structure.db 有冇登記"""
        return self.store.map_to_local(module_name, table, raw_json)

    def upsert_local(self, module_name, table, key_column, key_value,
                     data=None):
        """真實 upsert local（冪等）"""
        return self.store.upsert_local(module_name, table, key_column,
                                       key_value, data)

    def verify_count(self, module_name, table, expected=None):
        """真實 verify count：count(*) 對比 expected"""
        return self.store.verify_count(module_name, table, expected)

    def backup_table(self, module_name, table):
        """真實 backup：CREATE TABLE backup AS SELECT"""
        return self.store.backup_table(module_name, table)

    def create_new_table(self, module_name, table, ddl=None):
        """真實 create new table"""
        return self.store.create_new_table(module_name, table, ddl)

    def copy_rows(self, module_name, src_table, dst_table):
        """真實 copy rows"""
        return self.store.copy_rows(module_name, src_table, dst_table)

    def swap_table(self, module_name, new_table, old_table):
        """真實 swap：RENAME"""
        return self.store.swap_table(module_name, new_table, old_table)

    def verify_foreign_keys(self, module_name, table=None):
        """真實 verify foreign keys：PRAGMA foreign_key_check"""
        return self.store.verify_foreign_keys(module_name, table)

    def inspect(self, module_name, table):
        """真實 inspect（migrate_other）"""
        return self.store.inspect(module_name, table)

    def action(self, module_name, table, action_type="migrate_log"):
        """真實 action（migrate_other）：寫 migration_log"""
        return self.store.action(module_name, table, action_type)

    def verify(self, module_name, table, expected=None):
        """真實 verify（migrate_other）"""
        return self.store.verify(module_name, table, expected)

    def close(self):
        self.store.close()
