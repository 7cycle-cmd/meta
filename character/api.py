"""api.py — character.db 對外 API"""

from .sql import SqlStore


class Character:
    """字符定義（character.db）嘅對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def charset_values(self, table):
        """一個字符集嘅全部字符（set[str]）—— symbol / letter / INT"""
        return self.store.charset_values(table)

    def charset_rows(self, table):
        """一個字符集嘅全部行（list[dict]）"""
        return self.store.charset_rows(table)

    def symbols(self):
        return self.store.charset_values("symbol")

    def letters(self):
        return self.store.charset_values("letter")

    def ints(self):
        return self.store.charset_values("INT")

    def close(self):
        self.store.close()