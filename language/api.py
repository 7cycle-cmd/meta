"""api.py — language 對外 API（語言 + 顯示文字字典）

2026-10-25：language 表由 definition.db 搬嚟 + display_text 新表。
"""

from .sql import SqlStore


class Language:
    """語言字典（language.db）嘅對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def list_languages(self, active_only=True):
        """列出全部語言"""
        return self.store.languages(active_only)

    def add_language(self, meta, description=None):
        """新增語言（冪等）"""
        return self.store.add_language(meta, description)

    def list_display_texts(self, active_only=True):
        """列出全部顯示文字"""
        return self.store.display_texts(active_only)

    def add_display_text(self, meta, description=None):
        """新增顯示文字（冪等）"""
        return self.store.add_display_text(meta, description)

    def close(self):
        self.store.close()
