"""api.py — value.db 對外 API（值資產層）"""

from .sql import SqlStore


class Value:
    """值資產（value.db）嘅對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def add(self, value, taxonomy_id=None):
        """新增 / 攞一個值嘅 id（冪等）

        taxonomy_id = taxonomy.registry.id（邊個 module 登記）
        """
        return self.store.add(value, taxonomy_id)

    def get(self, value_id):
        """按 id 攞一個值"""
        return self.store.get(value_id)

    def by_value(self, value):
        """按值攞行（唔存在 None）"""
        return self.store.by_value(value)

    def list(self, taxonomy_id=None, active_only=True):
        """列出值（可按 module 篩選）"""
        return self.store.list(taxonomy_id, active_only)

    def count(self):
        return self.store.count()

    def close(self):
        self.store.close()