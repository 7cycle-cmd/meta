"""api.py — resource 對外 API"""

from .sql import SqlStore


class Resource:
    """resource 對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def close(self):
        self.store.close()
