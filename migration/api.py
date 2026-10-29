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

    def flow_registry(self, active_only=True):
        """列出 flow_registry（6 個 skill 檔案 + 真實行數）"""
        sql = "SELECT * FROM flow_registry"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.store.conn.execute(sql)]

    def step_registry(self, flow_registry_id=None, active_only=True):
        """列出 step_registry（每個 skill 檔案嘅 function + 行號）"""
        sql = ("SELECT sr.*, fr.filename"
               " FROM step_registry sr"
               " LEFT JOIN flow_registry fr ON fr.id = sr.flow_registry_id")
        args = ()
        where = []
        if flow_registry_id is not None:
            where.append("sr.flow_registry_id = ?")
            args = (flow_registry_id,)
        if active_only:
            where.append("sr.is_active = 1")
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY sr.flow_registry_id, sr.line_number"
        return [dict(r) for r in self.store.conn.execute(sql, args)]

    def check_column(self, module_name, table, column):
        """真實檢查：column 存唔存在（PRAGMA table_info 權威）

        已搬去 skill.py（SchemaSkill，2026-10-29 用戶要求）。
        """
        from .skill.schema import SchemaSkill
        s = SchemaSkill()
        try:
            return s.check_column(module_name, table, column)
        finally:
            s.close()

    def add_column(self, module_name, table, column, column_type="TEXT"):
        """真實加欄位（ALTER TABLE ADD COLUMN；冪等）

        已搬去 skill.py（SchemaSkill，2026-10-29 用戶要求）。
        """
        from .skill.schema import SchemaSkill
        s = SchemaSkill()
        try:
            return s.add_column(module_name, table, column, column_type)
        finally:
            s.close()

    def inspect_table(self, module_name, table):
        """真實 inspect：PRAGMA table_info 攞欄位清單（skill.py）"""
        from .skill.schema import SchemaSkill
        s = SchemaSkill()
        try:
            return s.inspect_table(module_name, table)
        finally:
            s.close()

    def backfill_column(self, module_name, table, column):
        """真實回填：count 有值 row 數（skill.py）"""
        from .skill.schema import SchemaSkill
        s = SchemaSkill()
        try:
            return s.backfill_column(module_name, table, column)
        finally:
            s.close()

    def verify_column(self, module_name, table, column):
        """真實 verify：PRAGMA 確認欄位存在（skill.py）"""
        from .skill.schema import SchemaSkill
        s = SchemaSkill()
        try:
            return s.verify_column(module_name, table, column)
        finally:
            s.close()

    def verify_rowcount(self, module_name, table):
        """真實 verify rowcount：count(*)（skill.py）"""
        from .skill.schema import SchemaSkill
        s = SchemaSkill()
        try:
            return s.verify_rowcount(module_name, table)
        finally:
            s.close()

    def report(self, module_name=None, table=None):
        """真實 report：migration_log 統計（skill.py）"""
        from .skill.schema import SchemaSkill
        s = SchemaSkill()
        try:
            return s.report(module_name, table)
        finally:
            s.close()

    def check_dictionary(self, module_name, table):
        """真實 check dictionary：已有值清單（skill/seed.py）"""
        from .skill.seed import SeedSkill
        s = SeedSkill()
        try:
            return s.check_dictionary(module_name, table)
        finally:
            s.close()

    def check_symbol(self, module_name, table, symbol, column="symbol"):
        """真實 check symbol：有冇呢個 symbol（skill/seed.py）"""
        from .skill.seed import SeedSkill
        s = SeedSkill()
        try:
            return s.check_symbol(module_name, table, symbol, column)
        finally:
            s.close()

    def insert_symbol(self, module_name, table, symbol, description=None,
                      column="symbol"):
        """真實 insert symbol（冪等）（skill/seed.py）"""
        from .skill.seed import SeedSkill
        s = SeedSkill()
        try:
            return s.insert_symbol(module_name, table, symbol,
                                   description, column)
        finally:
            s.close()

    def verify_symbol(self, module_name, table, symbol, column="symbol"):
        """真實 verify symbol：SELECT 確認存在（skill/seed.py）"""
        from .skill.seed import SeedSkill
        s = SeedSkill()
        try:
            return s.verify_symbol(module_name, table, symbol, column)
        finally:
            s.close()

    def check_source(self, module_name, table=None):
        """真實 check source：source 表記錄數（skill/sync.py）"""
        from .skill.sync import SyncSkill
        s = SyncSkill()
        try:
            return s.check_source(module_name, table)
        finally:
            s.close()

    def fetch_external(self, module_name, url, table="postman_sync"):
        """真實 fetch external：POST 記錄（skill/sync.py）"""
        from .skill.sync import SyncSkill
        s = SyncSkill()
        try:
            return s.fetch_external(module_name, url, table)
        finally:
            s.close()

    def map_to_local(self, module_name, table, raw_json=None):
        """真實 map：structure.db 有冇登記（skill/sync.py）"""
        from .skill.sync import SyncSkill
        s = SyncSkill()
        try:
            return s.map_to_local(module_name, table, raw_json)
        finally:
            s.close()

    def upsert_local(self, module_name, table, key_column, key_value,
                     data=None):
        """真實 upsert local（冪等）（skill/sync.py）"""
        from .skill.sync import SyncSkill
        s = SyncSkill()
        try:
            return s.upsert_local(module_name, table, key_column,
                                  key_value, data)
        finally:
            s.close()

    def verify_count(self, module_name, table, expected=None):
        """真實 verify count：count(*) 對比 expected（skill/sync.py）"""
        from .skill.sync import SyncSkill
        s = SyncSkill()
        try:
            return s.verify_count(module_name, table, expected)
        finally:
            s.close()

    def backup_table(self, module_name, table):
        """真實 backup：CREATE TABLE backup AS SELECT（skill/cutover.py）"""
        from .skill.cutover import CutoverSkill
        s = CutoverSkill()
        try:
            return s.backup_table(module_name, table)
        finally:
            s.close()

    def create_new_table(self, module_name, table, ddl=None):
        """真實 create new table（skill/cutover.py）"""
        from .skill.cutover import CutoverSkill
        s = CutoverSkill()
        try:
            return s.create_new_table(module_name, table, ddl)
        finally:
            s.close()

    def copy_rows(self, module_name, src_table, dst_table):
        """真實 copy rows（skill/cutover.py）"""
        from .skill.cutover import CutoverSkill
        s = CutoverSkill()
        try:
            return s.copy_rows(module_name, src_table, dst_table)
        finally:
            s.close()

    def swap_table(self, module_name, new_table, old_table):
        """真實 swap：RENAME（skill/cutover.py）"""
        from .skill.cutover import CutoverSkill
        s = CutoverSkill()
        try:
            return s.swap_table(module_name, new_table, old_table)
        finally:
            s.close()

    def verify_foreign_keys(self, module_name, table=None):
        """真實 verify foreign keys：PRAGMA foreign_key_check（skill/cutover.py）"""
        from .skill.cutover import CutoverSkill
        s = CutoverSkill()
        try:
            return s.verify_foreign_keys(module_name, table)
        finally:
            s.close()

    def inspect(self, module_name, table):
        """真實 inspect（migrate_other）（skill/other.py）"""
        from .skill.other import OtherSkill
        s = OtherSkill()
        try:
            return s.inspect(module_name, table)
        finally:
            s.close()

    def action(self, module_name, table, action_type="migrate_log"):
        """真實 action（migrate_other）：寫 migration_log（skill/other.py）"""
        from .skill.other import OtherSkill
        s = OtherSkill()
        try:
            return s.action(module_name, table, action_type)
        finally:
            s.close()

    def verify(self, module_name, table, expected=None):
        """真實 verify（migrate_other）（skill/other.py）"""
        from .skill.other import OtherSkill
        s = OtherSkill()
        try:
            return s.verify(module_name, table, expected)
        finally:
            s.close()

    def close(self):
        self.store.close()
