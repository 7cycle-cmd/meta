"""api.py — guard.db 對外 API（token registry 守衛）"""

from .sql import SqlStore


class Guard:
    """寫入憑證守衛（guard.db registry）嘅對外介面

    2026-10-26 重建：守衛只存在於 rest_api（HTTP 入口）。
    registry = token 登記表（rest_api 驗證 ?token=/X-API-Token）。

    用法：
        from guard import Guard
        g = Guard()
        g.register_token('terminology.api', module_id=4)
        g.valid_token('terminology.api')   # True / False
        g.close()
    """

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def register(self, token_id, module_id, file_id=None):
        """登記一個 token（冪等）"""
        return self.store.register_token(token_id, module_id, file_id)

    def register_many(self, items):
        """一次過登記多個 token [(token_id, module_id), ...]"""
        return self.store.register_many(items)

    def valid(self, token_id, active_only=True):
        """驗證 token 有冇效（存在 + is_active=1）"""
        return self.store.valid_token(token_id, active_only)

    def token_row(self, token_id, active_only=True):
        """攞 token 行"""
        return self.store.token_row(token_id, active_only)

    def tokens(self, active_only=True):
        """列出全部 token"""
        return self.store.tokens(active_only)

    def count(self):
        return self.store.count()

    def close(self):
        self.store.close()
