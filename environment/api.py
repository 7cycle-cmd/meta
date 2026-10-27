"""api.py — environment.db 對外 API（執行環境）"""

from .sql import SqlStore


class Environment:
    """環境層（computer / IDE / Browser / APP + 設定 + 熱鍵）嘅對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def list_types(self, active_only=True):
        """列出環境類型（computer / IDE / Browser / APP）"""
        return self.store.types(active_only)

    def list_identities(self, type_id=None):
        """列出實際環境（可按類型篩選）"""
        return self.store.identities(type_id)

    def list_settings(self, active_only=True):
        """列出環境設定字典（permission / delegate / mode ...）"""
        return self.store.settings(active_only)

    def list_hotkeys(self, setting_id=None):
        """列出設定 × 熱鍵（可按設定篩選）"""
        return self.store.hotkeys(setting_id)

    def list_buttons(self, active_only=True):
        """列出鍵盤按鈕字典"""
        return self.store.buttons(active_only)

    def list_options(self, active_only=True):
        """列出設定選項字典"""
        return self.store.options(active_only)

    def list_setting_values(self, setting_id=None):
        """列出設定 × 選項對應"""
        return self.store.setting_values(setting_id)

    def close(self):
        self.store.close()
