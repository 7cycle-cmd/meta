"""api.py — structure.db 對外 API（結構層）

結構層字典：db_field_type / db_field_format /
                db_field_unique / db_field_property /
                db_field_check / db_table_setting
fallback 值字典 = common.boolean（0/1；db_field_default 已移除 2026-10-25；
default_value_text 已移除 2026-10-26）
欄位實例嘅唯一擁有者 = resource.db db_field（db_field_type 提供型別）
2026-10-27（用戶要求）：allowed_symbol / registry 表已移除。
"""

from .sql import SqlStore


class Structure:
    """DB 結構層（structure.db）嘅對外介面：欄位型別 + 設定 pattern"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def list_data_types(self, status=None):
        """列出欄位規格字典（db_field_setting JOIN type + format）"""
        return self.store.data_types(status)

    def list_db_field_uniques(self, active_only=True):
        """列出 unique 欄位名字典（db_field_unique）"""
        return self.store.db_field_uniques(active_only)

    def list_db_field_xxxxs(self, active_only=True):
        """列出欄位規格組合表（db_field_setting，舊名 alias）"""
        return self.store.db_field_xxxxs(active_only)

    def list_db_field_checks(self, db_field_property_id=None, active_only=True):
        """列出 CHECK 約束（db_field_check JOIN property）"""
        return self.store.db_field_checks(db_field_property_id, active_only)

    def add_db_field_check(self, db_field_property_id, boolean_id=None):
        """加一個 CHECK 約束（冪等：db_field_property_id）

        boolean_id 保留相容（忽略；值域由 property 表達）
        """
        return self.store.add_db_field_check(
            db_field_property_id, boolean_id)

    def list_db_field_settings(self, active_only=True):
        """列出欄位規格組合表（db_field_setting，2026-10-25 rebuild）"""
        return self.store.db_field_settings(active_only)

    def list_db_field_formats(self, active_only=True):
        """列出原子格式 token 字典（db_field_format）"""
        return self.store.db_field_formats(active_only)

    # ---------- default_value（2026-10-26：表驅動，唔寫 code） ----------
    def list_default_values(self, active_only=True):
        """列出全部 default_value（JOIN 型別名）"""
        return self.store.default_values(active_only)

    def add_default_value(self, db_field_type_id, value):
        """登記一個型別嘅預設值（冪等；同時標記 db_field_type.default_value=1）"""
        return self.store.add_default_value(db_field_type_id, value)

    def remove_default_value(self, db_field_type_id):
        """移除一個型別嘅預設值（冪等；同時標記 default_value=0）"""
        return self.store.remove_default_value(db_field_type_id)

    def add_db_table_setting(self, meta_key,
                             db_field_format_id, seq_id=None):
        """加一個通用欄位定義（冪等）

        meta_key            = 欄位名（id / meta / created_at...）
        db_field_format_id  = db_field_setting.id（欄位規格組合）
        seq_id              = common.seq.id（欄位次序，2026-10-27）
        """
        return self.store.add_db_table_setting(
            meta_key, db_field_format_id, seq_id)

    def set_position(self, setting_id, seq_id):
        """設定欄位定義嘅次序（by_id，common.seq.id）"""
        return self.store.set_position(setting_id, seq_id)

    def set_seq(self, setting_id, seq_id):
        """（2026-10-27 新名）設定欄位定義嘅次序（common.seq.id）"""
        return self.store.set_position(setting_id, seq_id)

    def list_db_table_settings(self, active_only=True):
        """列出通用欄位模板（db_table_setting，一行 = 一個欄位）"""
        return self.store.db_table_settings(active_only)

    def list_positions(self, active_only=True):
        """列出位置字典（seq：package 內第幾張表 / 欄位次序）"""
        return self.store.positions(active_only)

    def list_seqs(self, active_only=True):
        """列出 seq 字典（2026-10-27 用戶要求）"""
        return self.store.seqs(active_only)

    def package_tables_ddl(self, package_meta):
        """由 taxonomy 定義自動生成 CREATE TABLE DDL

        package_meta = module 名（taxonomy.taxonomy，tree = module）
        每個 module 建 DB 時 call 呢個，自動有齊定義好嘅表。
        """
        return self.store.package_tables_ddl(package_meta)

    # ---------- structure_type / structure_file（file 層 = 真檔名） ----------
    def list_structure_types(self, active_only=True):
        """列出實體類型字典（1=package 2=file 3=db_table 4=db_field 5=db 6=root）"""
        return self.store.structure_types(active_only)

    def list_structure_addresses(self, active_only=True):
        """列出實體地址字典（structure_address：type -> value）"""
        return self.store.structure_addresses(active_only)

    def list_structure_taxonomies(self, active_only=True):
        """列出樹層 ↔ 實體類型映射（structure_taxonomy）"""
        return self.store.structure_taxonomies(active_only)

    def list_structure_files(self, module_id=None, active_only=True):
        """列出實體檔案（可按 module 篩選）"""
        return self.store.structure_files(module_id, active_only)

    def list_structure_functions(self, module_id=None, active_only=True):
        """列出 structure_function（可按 module 篩選，2026-10-28）"""
        return self.store.structure_functions(module_id, active_only)

    def sync_structure_functions(self, module_name=None):
        """AST 掃描 function 地址入 structure_function（2026-10-28）"""
        return self.store.sync_structure_functions(module_name)

    def register_structure_file(self, module_id, file_name, file_type_id=None):
        """登記一個實體檔案（冪等）—— file 層行（structure_module）

        file_type_id 保留相容（2026-10-26 已移除 file_type 字典）。
        """
        return self.store.insert_structure_file(module_id, file_name,
                                                file_type_id)

    # ---------- table_definition / db_field（2026-10-24 真表結構定義） ----------
    # 2026-10-26 redesign：structure_db_table by_id（channel_id + module_id）。
    def list_table_definitions(self, active_only=True, channel_id=None,
                               module_id=None):
        """列出全部表定義（structure_db_table，含欄位清單）

        channel_id / module_id 可選篩選（by_id，2026-10-26）。
        """
        return self.store.table_definitions(
            active_only, channel_id=channel_id, module_id=module_id)

    def get_table_definition(self, db_file, table_name, active_only=True):
        """攞一個表定義（by db_file + table_name，含欄位清單）"""
        return self.store.table_definition(db_file, table_name, active_only)

    def register_table_definition(self, table_name, db_file, description=None,
                                  module_scope=0, channel_id=None,
                                  module_id=None):
        """登記一張表（冪等，channel_id + module_id + table_name unique）

        2026-10-26：by_id。channel_id/module_id 傳入就唔用 db_file 反查。
        module_scope 保留兼容（忽略）。
        """
        return self.store.add_table_definition(
            table_name, db_file, description, module_scope,
            channel_id=channel_id, module_id=module_id)

    def register_db_table(self, channel_id, module_id, table_name,
                          description=None):
        """（新 API，by_id）登記一張真表（冪等）"""
        return self.store.add_db_table(
            channel_id, module_id, table_name, description)

    def register_db_field(self, table_id, field_name, description=None):
        """（新 API，by_id）登記一個真欄位（冪等）"""
        return self.store.add_db_field_by_table(
            table_id, field_name, description)

    def add_db_field(self, db_file, table_name, column_name, setting_pattern,
                     position_id=None):
        """加一欄去一個表定義（冪等）

        setting_pattern = db_field_xxxx.id 或 db_field_format 名（unique / NULL...）
        """
        return self.store.add_table_column(
            db_file, table_name, column_name, setting_pattern,
            position_id=position_id)

    # 2026-10-25：舊名 alias（table_column -> db_field）
    def add_table_column(self, db_file, table_name, column_name, setting_pattern,
                         position_id=None):
        """（舊名）加一欄去一個表定義 —— 已改名 add_db_field"""
        return self.add_db_field(
            db_file, table_name, column_name, setting_pattern,
            position_id=position_id)

    def generate_table_ddl(self, db_file, table_name):
        """由 table_definition 生成一張表嘅 CREATE TABLE DDL

        db_file / table_name 指定邊張表（db_file + table_name unique）
        有定義用定義；冇定義 -> 用 db_table_setting 通用模板。
        """
        return self.store.generate_table_ddl(db_file, table_name)

    def set_type_status(self, type_id, status):
        """設定 type 狀態：active / legacy / dead"""
        return self.store.set_type_status(type_id, status)

    def cleanup_types(self, status="dead"):
        """清理 type：將指定狀態（legacy/dead）標記 is_active=0"""
        return self.store.cleanup_types(status)

    def close(self):
        self.store.close()