"""api.py — option.db 對外 API"""

from .sql import SqlStore


class Option:
    """值域定義（option.db）嘅對外介面

    每個資源 / 欄位（resource.db registry.id 或 structure.db 結構 id）
    可以有允許值清單。呢個係定義層 —— 唔執行，只定義「邊啲值合法」。
    """

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def options(self, resource_id=None, structure_db_field_id=None,
                active_only=True):
        """一個資源 / 欄位嘅允許值清單"""
        return self.store.options(resource_id, structure_db_field_id,
                                  active_only)

    def add_option(self, resource_id=None, value=None, description=None,
                   structure_db_field_id=None, structure_db_table_id=None):
        """加一個允許值（冪等）

        resource_id 或 structure_db_field_id 至少一個。
        """
        return self.store.add_option(
            resource_id, value, description,
            structure_db_field_id, structure_db_table_id)

    def has_option(self, resource_id=None, value=None,
                   structure_db_field_id=None, active_only=True):
        """呢個值喺唔喺允許清單"""
        return self.store.has_option(resource_id, value,
                                     structure_db_field_id, active_only)

    def remove_option(self, resource_id=None, value=None,
                      structure_db_field_id=None):
        self.store.remove_option(resource_id, value, structure_db_field_id)

    def all_options(self, active_only=True):
        """全部允許值"""
        return self.store.all_options(active_only)

    def reset(self):
        """reset：清空全部 option（重新開始）"""
        self.store.reset()

    def close(self):
        self.store.close()