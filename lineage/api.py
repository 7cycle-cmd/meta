"""api.py — lineage.db 對外 API（值嘅運行時條件）"""

from .sql import SqlStore


class Lineage:
    """值嘅運行時條件（lineage.db）嘅對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def add(self, value_id, run_id=None, flow_id=None, step_id=None,
            resource_id=None, taxonomy_id=None, value=None):
        """記錄一個值嘅運行時條件（冪等）"""
        return self.store.add(value_id, run_id, flow_id, step_id,
                              resource_id, taxonomy_id, value)

    def list(self, value_id=None, run_id=None, flow_id=None,
             taxonomy_id=None, active_only=True, limit=100):
        """列出運行時條件"""
        return self.store.list(value_id, run_id, flow_id, taxonomy_id,
                               active_only, limit)

    def count(self):
        return self.store.count()

    def close(self):
        self.store.close()