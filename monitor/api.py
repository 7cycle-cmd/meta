"""api.py — monitor 對外 API（全站當前計數快照）"""

from .sql import SqlStore


class Monitor:
    """全站當前計數（monitor.db）嘅對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def refresh(self):
        """更新兩張快照表（冪等）"""
        return self.store.refresh()

    def refresh_structure(self):
        """更新 current_structure"""
        return self.store.refresh_structure()

    def refresh_taxonomy(self):
        """更新 current_taxonomy"""
        return self.store.refresh_taxonomy()

    def refresh_field_check(self):
        """更新 db_field_check 快照（json_not_integer 監控）"""
        return self.store.refresh_field_check()

    def refresh_source_register(self):
        """更新 source_register 快照（詞 -> source 選擇）"""
        return self.store.refresh_source_register()

    def refresh_sweep(self):
        """更新 sweep 快照（清理狀態）"""
        return self.store.refresh_sweep()

    def refresh_fallback(self):
        """更新 fallback 快照（後備值）"""
        return self.store.refresh_fallback()

    def refresh_rest_api_read(self):
        """更新 rest_api_READ 中心（全站 READ API）"""
        return self.store.refresh_rest_api_read()

    def refresh_rest_api_watch(self):
        """更新 rest_api_watch（expected vs actual 比對）

        返回 {"ready": n, "missing": n, "new": n, "total": n}
        """
        return self.store.refresh_rest_api_watch()

    def list_rest_api_watch(self, status=None, active_only=True):
        """列出 REST API 就緒度監控（可按 status 篩選）"""
        return self.store.current_rest_api_watch(status, active_only)

    def list_current_structure(self, active_only=True):
        """列出 structure 各實體類型當前行數"""
        return self.store.current_structure(active_only)

    def list_current_taxonomy(self, active_only=True):
        """列出 taxonomy 各樹層當前行數"""
        return self.store.current_taxonomy(active_only)

    def list_field_check(self, active_only=True):
        """列出 db_field_check 快照（含 json_not_integer 狀態）"""
        return self.store.current_field_check(active_only)

    def list_source_register(self, active_only=True):
        """列出 source_register 快照（詞 -> source 選擇）"""
        return self.store.current_source_register(active_only)

    def list_sweep(self, active_only=True):
        """列出 sweep 快照（清理狀態）"""
        return self.store.current_sweep(active_only)

    def list_fallback(self, active_only=True):
        """列出 fallback 快照（後備值）"""
        return self.store.current_fallback(active_only)

    def list_rest_api_read(self, active_only=True):
        """列出 READ API 中心（全站 READ API）"""
        return self.store.current_rest_api_read(active_only)

    def list_skills(self, active_only=True):
        """列出 fallback 快照（後備值）"""
        return self.store.current_fallback(active_only)

    def list_skills(self, active_only=True):
        """列出 monitor 技能（skill 表）"""
        return self.store.skills(active_only)

    def close(self):
        self.store.close()
