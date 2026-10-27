"""api.py — definition.db 對外 API（定義層：類型/規則/語言/符號/模板）"""

from .sql import SqlStore

from .function import *  # noqa: F401,E402


class Definition:
    """DB 定義層（definition.db）嘅對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def list_table_settings(self, active_only=True):
        """列出通用欄位模板（db_table_setting，一行 = 一個欄位）"""
        return self.store.table_settings(active_only)

    def list_rules(self):
        return self.store.rules()

    # ---------- structure_file（實體檔案字典，v2：file 層 = 真檔名） ----------
    # physical_package 已移除（2026-10-25：system_setting.physical_location 取代）。
    # 2026-10-26：file_type / structure_file 表移除 —— file 層直接存真檔名
    # （structure_module file 行，by structure API）。
    def list_structure_files(self, module_id=None, active_only=True):
        """列出實體檔案（可按 module_id 篩選）"""
        return self.store.structure_files(module_id, active_only)

    def list_modules_files(self, module_name=None, active_only=True):
        """列出 module 嘅檔案（by system_setting 攞 module 名）"""
        return self.store.modules_files(module_name, active_only)

    def register_file(self, module_id, file_name, file_type_id=None):
        """登記一個實體檔案（冪等，file 層行 = 真檔名）

        file_type_id 保留相容（2026-10-26 已移除 file_type 字典）。
        """
        return self.store.insert_structure_file(module_id, file_name,
                                                file_type_id)

    # ---------- package（taxonomy.package 權威） ----------
    def list_package_settings(self, active_only=True):
        """列出 package（taxonomy.package：meta / folder / db_file）"""
        return self.store.package_settings(active_only)

    # ---------- file_required（必需檔案規則 = DEFAULT_FILE_TYPES code 常數） ----------
    def list_file_types(self, active_only=True):
        """列出檔案類型字典（file_required 權威來源；由 code 常數提供）"""
        return self.store.file_requireds(active_only)

    def list_file_requireds(self, active_only=True):
        """列出必須檔案字典（required=True 嘅 DEFAULT_FILE_TYPES）"""
        return self.store.file_requireds(active_only)

    def required_file_types(self):
        """必須有嘅檔案類型（is_required = 1）"""
        return self.store.required_file_types()

    # ---------- db_table_required / db_field_required（必需表/欄位） ----------
    # 字典（table_definition / db_field）喺 structure —— by API。
    def list_db_table_requireds(self, active_only=True):
        """列出必需表（table_definition_id 指 structure）"""
        return self.store.db_table_requireds(active_only)

    def required_tables(self):
        """必須有嘅表（db_table_required 存在即必需）"""
        return self.store.required_tables()

    def add_db_table_required(self, table_name, db_file="*.db", position=1):
        """登記一張必需表（冪等）—— 字典喺 structure，position 喺 common"""
        return self.store.add_db_table_required(table_name, db_file, position)

    def list_db_field_requireds(self, table_definition_id=None,
                                active_only=True):
        """列出必需欄位（可按表篩選）"""
        return self.store.db_field_requireds(table_definition_id,
                                             active_only)

    def add_db_field_required(self, table_name, column_name, db_file="*.db",
                              position=1):
        """登記一個必需欄位（冪等）—— 字典喺 structure，position 喺 common"""
        return self.store.add_db_field_required(
            table_name, column_name, db_file, position)

    def sync_physical(self):
        """掃 module 資料夾，自動登記 structure_file"""
        return self.store._sync_physical()

    # ---------- structure_type / structure_required（實體分類 + 大類要求） ----------
    def list_structure_types(self, active_only=True):
        """列出實體類型字典（1=package 2=file 3=db_table 4=db_field 5=db）"""
        return self.store.structure_types(active_only)

    def list_structure_requireds(self, tree_meta=None, active_only=True):
        """列出每個大類（channel/module/skill）必須有咩實體

        tree_meta = taxonomy.tree.meta_key（channel / module / skill）
        """
        return self.store.structure_requireds(tree_meta, active_only)

    def check_module_files(self, module_id=None, module_name=None):
        """檢查一個 module 嘅檔案結構（取代 module_file 嘅 check_complete）

        標準 = file_required（存在 = 必需，唔硬編碼）：
            1. actual 資料夾內 required 檔喺唔喺度（實體檢查）
            2. physical_file 字典（sync_physical 自動登記嘅實際檔案）
        module 名優先：由 module_name / system_setting（module 名權威）。

        返回 {"complete": bool, "missing": [...], "files": [...],
              "required": [...], "virtual": bool, "module_id": int|None}
        """
        import os
        req = self.store.required_file_types()
        required = [(r["meta"][:-3] if r["meta"].endswith(".py") else r["meta"],
                     r["meta"]) for r in req]
        required_types = [t for t, _ in required]
        # module 名 + module_id：taxonomy.registry 權威（2026-10-26
        # 取代 system_setting；package 表已移除，module 清單 = registry 表；
        # 2026-10-27 taxonomy rename 做 registry）
        name = module_name
        mid = module_id
        try:
            import sqlite3 as _sq
            tc = _sq.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
            tc.row_factory = _sq.Row
            try:
                if name:
                    r = tc.execute(
                        "SELECT t.id, t.meta FROM registry t"
                        " JOIN tree tr ON tr.id = t.tree_id"
                        " WHERE tr.meta_key = 'module' AND t.meta = ?"
                        " AND t.is_active = 1", (name,)).fetchone()
                    if r:
                        mid = r["id"]
                elif mid is not None:
                    r = tc.execute(
                        "SELECT t.id, t.meta FROM registry t"
                        " JOIN tree tr ON tr.id = t.tree_id"
                        " WHERE tr.meta_key = 'module' AND t.id = ?"
                        " AND t.is_active = 1", (mid,)).fetchone()
                    if r:
                        name = r["meta"]
            finally:
                tc.close()
        except Exception:
            pass
        folder = None
        if name and os.path.isdir(os.path.join(r"C:\projects\meta", name)):
            folder = os.path.join(r"C:\projects\meta", name)
        if folder is None and mid is None:
            return {"complete": True, "missing": [], "files": [],
                    "required": required_types, "virtual": True,
                    "module_id": None}
        # 1. actual 資料夾檢查
        on_disk = set()
        if folder:
            on_disk = {fn[:-3] for fn in os.listdir(folder)
                       if fn.endswith(".py")}
        # 2. file 層字典檢查（structure_module file 行 = sync 自動登記嘅實際檔案）
        in_db = set()
        files = []
        if mid is not None:
            files = self.store.structure_files(module_id=mid)
            in_db = {f["file_type"] or f["file_name"][:-3]
                     for f in files}
        have = in_db | on_disk
        missing = sorted(t for t in required_types if t not in have)
        return {"complete": len(missing) == 0, "missing": missing,
                "files": files, "required": required_types, "virtual": False,
                "module_id": mid}

    def discover_module_files(self):
        """discovery（定義層自動掃描）：全部 module 一次過對照 file_required

        掃 C:\\projects\\meta 有 __init__.py 嘅資料夾（即 _sync_physical 嘅對象），
        每個對照 file_required.is_required，回報邊啲缺失。

        返回 {"total": n, "complete": n, "missing": n, "report": {name: {...}}}
        """
        import os
        req = self.store.required_file_types()
        required = [r["meta"] for r in req]  # 完整檔名（api.py）
        required_types = [m[:-3] if m.endswith(".py") else m
                          for m in required]  # 去 .py（api）
        meta_dir = r"C:\projects\meta"
        report = {}
        for entry in sorted(os.listdir(meta_dir)):
            folder = os.path.join(meta_dir, entry)
            if not os.path.isdir(folder):
                continue
            if entry.startswith("_"):
                continue  # 臨時/備份
            if not os.path.isfile(os.path.join(folder, "__init__.py")):
                continue
            on_disk = {fn[:-3] for fn in os.listdir(folder)
                       if fn.endswith(".py")}
            missing = sorted(t for t in required_types if t not in on_disk)
            report[entry] = {
                "complete": len(missing) == 0,
                "missing": missing,
                "files": sorted(on_disk),
            }
        n_total = len(report)
        n_missing = sum(1 for r in report.values() if not r["complete"])
        return {"total": n_total, "complete": n_total - n_missing,
                "missing": n_missing, "report": report}

    def report_missing_to_task(self, task_id=None):
        """discovery 發現缺失 -> 落 task 訂單（有 action 嘅人接手）

        每個缺失 module 開一個 task：
            action = fill-missing-files（唔喺 flow.db 都唔阻塞 —— 冇 flow 就淨做）
            params = {"module": name, "missing": [file_type...],
                      "required_files": [api.py, ...]}
        已有 pending 同名 task（module 一樣 + action 一樣）-> 唔重複落。

        返回 {"task_total": n, "new_tasks": [task_id...], "report": {module: {...}}}
        """
        import json as _json
        self.sync_physical()  # 先確保 physical_file 最新
        disc = self.discover_module_files()
        # 2026-10-26：guard/task 已刪除 -> 唔再落 task 訂單
        #（report_missing_to_task 只返回報告，冇 task 佢自行處理）
        new_tasks = []
        dup = 0
        for name, info in disc["report"].items():
            if info["complete"]:
                continue
            missing_types = info["missing"]
            dup += 1
        return {"task_total": len(new_tasks) + dup, "new_tasks": new_tasks,
                "dup": dup, "report": disc["report"]}

    # ---------- 條件定義（code_condition 純定義，零執行） ----------
    def list_subjects(self, active_only=True):
        """列出主體字典（例如 api.py 嘅 do_GET）"""
        return self.store.subjects(active_only)

    def register_subject(self, value, description=None, resource_id=None):
        """登記一個主體（幂等）"""
        return self.store.add_subject(value, description, resource_id)

    def list_operators(self, active_only=True):
        """列出條件運算字典（必須 / 唔可以 / 至少一次）"""
        return self.store.operators(active_only)

    def register_operator(self, value, description=None, resource_id=None):
        """登記一個條件運算（幂等）"""
        return self.store.add_operator(value, description, resource_id)

    def list_expected_defs(self, active_only=True):
        """列出期望值字典（例如 /health 一定要有 route）"""
        return self.store.expected_defs(active_only)

    def register_expected_def(self, value, description=None,
                              resource_id=None):
        """登記一個期望值（幂等）"""
        return self.store.add_expected_def(value, description, resource_id)

    def list_code_conditions(self, active_only=True):
        """列出全部條件定義（subject × operator × expected，JOIN 名）"""
        return self.store.code_conditions(active_only)

    def register_code_condition(self, subject, operator, expected,
                                description=None):
        """建立一條條件定義（幂等，三邊字典自動註冊）"""
        return self.store.add_code_condition(subject, operator, expected,
                                             description)

    def close(self):
        self.store.close()