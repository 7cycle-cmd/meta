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

    def list_current_structure(self, active_only=True):
        """列出 structure 各實體類型當前行數"""
        return self.store.current_structure(active_only)

    def list_current_taxonomy(self, active_only=True):
        """列出 taxonomy 各樹層當前行數"""
        return self.store.current_taxonomy(active_only)

    def close(self):
        self.store.close()
