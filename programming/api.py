"""api.py — programming.db 對外 API"""

from .sql import SqlStore


class Programming:
    """程式語言/格式/組合（programming.db）嘅對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def languages(self, active_only=True):
        return self.store.languages(active_only)

    def language_aliases(self, active_only=True):
        return self.store.language_aliases(active_only)

    def data_formats(self, active_only=True):
        return self.store.data_formats(active_only)

    def owners(self, active_only=True):
        return self.store.owners(active_only)

    def owner_letters(self, owner_id):
        return self.store.owner_letters(owner_id)

    def owner_symbols(self, owner_id):
        return self.store.owner_symbols(owner_id)

    def owner_ints(self, owner_id):
        return self.store.owner_ints(owner_id)

    def start_chars(self, owner_id):
        return self.store.start_chars(owner_id)

    # ---------- 行級映射（2026-10-26） ----------
    def sync_line_mappings(self):
        """由真實來源重建行級映射表（package / file / line_ast /
        line_field / function_mapping，冪等）"""
        return self.store.sync_line_mappings()

    def line_asts(self, module_id=None, file_id=None, active_only=True):
        """列出 AST 行（可按 module / file 篩選）"""
        sql = "SELECT * FROM line_ast WHERE 1=1"
        args = []
        if module_id:
            sql += " AND module_id = ?"
            args.append(module_id)
        if file_id:
            sql += " AND file_id = ?"
            args.append(file_id)
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY module_id, file_id, line_number"
        return [dict(r) for r in self.store.conn.execute(sql, args)]

    def line_fields(self, module_id=None, active_only=True):
        """列出欄位檢查行（可按 module 篩選）"""
        sql = "SELECT * FROM line_field WHERE 1=1"
        args = []
        if module_id:
            sql += " AND module_id = ?"
            args.append(module_id)
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY module_id, file_id, line_number"
        return [dict(r) for r in self.store.conn.execute(sql, args)]

    def function_mappings(self, module_id=None, active_only=True):
        """列出 function 行號映射（line_ids JSON）"""
        sql = "SELECT * FROM function_mapping WHERE 1=1"
        args = []
        if module_id:
            sql += " AND module_id = ?"
            args.append(module_id)
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY module_id, function_id"
        return [dict(r) for r in self.store.conn.execute(sql, args)]

    # ---------- 欄位值域（db_field_value，2026-10-26） ----------
    def sync_db_field_values(self):
        """由真實 db_field 重建欄位值域（db_field_value，冪等）

        順手補 db_field_check（BOOLEAN 型別 -> [0,1] check）。
        """
        return self.store.sync_db_field_values()

    def db_field_values(self, structure_db_field_id=None,
                        db_field_check_id=None, active_only=True):
        """列出欄位值域（可按欄位 / check 篩選）"""
        sql = ("SELECT v.id, v.structure_db_field_id, v.db_field_check_id,"
               " v.is_active, v.created_at, v.updated_at"
               " FROM db_field_value v WHERE 1=1")
        args = []
        if structure_db_field_id is not None:
            sql += " AND v.structure_db_field_id = ?"
            args.append(structure_db_field_id)
        if db_field_check_id is not None:
            sql += " AND v.db_field_check_id = ?"
            args.append(db_field_check_id)
        if active_only:
            sql += " AND v.is_active = 1"
        sql += " ORDER BY v.id"
        return [dict(r) for r in self.store.conn.execute(sql, args)]

    # ---------- 程式語言證據（2026-10-27：source 官方網站可證明） ----------
    def sql_types(self, active_only=True):
        """列出 SQL 語句類型（DDL / DML）"""
        return self.store.sql_types(active_only)

    # ---------- Python 語法字典（2026-10-27 用戶設計：官方 sample = evidence） ----------
    def python_asts(self, active_only=True):
        """列出 Python AST 節點字典（docs.python.org 官方可證明）"""
        return self.store.python_asts(active_only)

    def find_python_ast(self, ast_name):
        """搵一個 AST 節點（冇 -> None）"""
        return self.store.find_python_ast(ast_name)

    def add_python_ast(self, ast_name, description=None, language_id=1):
        """登記一個 Python AST 節點（冪等）"""
        return self.store.add_python_ast(ast_name, description, language_id)

    def python_decorators(self, active_only=True):
        """列出 Python decorator 字典（官方/實務語法）"""
        return self.store.python_decorators_list(active_only)

    def find_python_decorator(self, decorator_name):
        """搵一個 decorator（冇 -> None）"""
        return self.store.find_python_decorator(decorator_name)

    def add_python_decorator(self, decorator_name, description=None,
                             language_id=1):
        """登記一個 Python decorator（冪等）"""
        return self.store.add_python_decorator(decorator_name, description,
                                                language_id)

    # ---------- *_allowed 語境允許表（2026-10-27 用戶設計） ----------
    def structure_types(self, active_only=True):
        """列出語境層級字典（module/channel/skill/db_table/db_field）"""
        return self.store.structure_types(active_only)

    def add_field_allowed(self, arg_id, structure_type_id=None,
                          data_format_type_id=None):
        """登記一條 field 允許（冪等）：arg 喺呢個語境+格式啱唔啱

        arg_id              = 參數名（attr / items ...）
        structure_type_id   = structure_type.id（module / db_table / db_field ...）
        data_format_type_id = data_format.id（json=5 / xml=6 / csv=7 / yaml=8）
        """
        return self.store.add_field_allowed(arg_id, structure_type_id,
                                            data_format_type_id)

    def add_starred_allowed(self, starred_id, structure_type_id=None,
                            data_format_type_id=None, allowed=None):
        """登記一條 Starred 允許（冪等）：*items 喺呢個語境+格式啱唔啱"""
        return self.store.add_starred_allowed(starred_id, structure_type_id,
                                              data_format_type_id, allowed)

    def add_sql_allowed(self, sql_type_id, value, db_table_id=None,
                        db_field_id=None, allowed=None):
        """登記一條 SQL 允許：呢句 SQL 對應嘅表/欄位啱唔啱（冪等）"""
        return self.store.add_sql_allowed(sql_type_id, value, db_table_id,
                                          db_field_id, allowed)

    def field_alloweds(self, active_only=True):
        """列出 field 允許清單"""
        return self.store.field_alloweds(active_only)

    def starred_alloweds(self, active_only=True):
        """列出 Starred 允許清單"""
        return self.store.starred_alloweds(active_only)

    def sql_alloweds(self, active_only=True):
        """列出 SQL 允許清單"""
        return self.store.sql_alloweds(active_only)

    def check_field_allowed(self, arg_id, structure_type_id=None,
                            data_format_type_id=None):
        """檢查一個 arg 喺語境啱唔啱"""
        return self.store.check_field_allowed(arg_id, structure_type_id,
                                               data_format_type_id)

    def check_starred_allowed(self, starred_id, structure_type_id=None,
                              data_format_type_id=None, value=None):
        """檢查一個 *items 喺語境啱唔啱"""
        return self.store.check_starred_allowed(starred_id, structure_type_id,
                                                data_format_type_id, value)

    def check_sql_allowed(self, sql_type_id, value, db_table_id=None,
                          db_field_id=None):
        """檢查一句 SQL 語句對應嘅表/欄位啱唔啱"""
        return self.store.check_sql_allowed(sql_type_id, value, db_table_id,
                                            db_field_id)

    def add_evidence_ast(self, source_id, language_id, value, ast_id=None):
        """登記一條 AST 節點證據（source 官方 spec 可證明，冪等）"""
        return self.store.add_evidence_ast(source_id, language_id, value,
                                           ast_id)

    def add_evidence_decorators(self, source_id, language_id, value,
                                decorators_id=None):
        """登記一條 decorator 證據（source 官方文件可證明，冪等）

        decorators_id = template.db decorator.id（可選）
        """
        return self.store.add_evidence_decorators(
            source_id, language_id, value, decorators_id)

    def add_evidence_sql(self, source_id, language_id, sql_type_id, value):
        """登記一條 SQL 語句證據（ISO/IEC 9075 可證明，冪等）"""
        return self.store.add_evidence_sql(source_id, language_id,
                                           sql_type_id, value)

    def evidence_asts(self, active_only=True):
        """列出 AST 節點證據"""
        return self.store.evidence_asts(active_only)

    def evidence_decorators(self, active_only=True):
        """列出 decorator 證據"""
        return self.store.evidence_decorators_list(active_only)

    def evidence_sqls(self, active_only=True):
        """列出 SQL 語句證據"""
        return self.store.evidence_sqls(active_only)

    def close(self):
        self.store.close()