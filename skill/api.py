"""skill registry 嘅對外 API。

2026-10-27（用戶要求 redesign）：
    registry 表：id | name | resource_formula_id | resource_structure_id
    module_skill 表已移除（drop）
"""

from .sql import SqlStore


class Skill:
    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def registry(self, active_only=True):
        return self.store.registry(active_only)

    def register(self, name, resource_formula_id=None,
                 resource_structure_id=None):
        return self.store.register(name, resource_formula_id,
                                   resource_structure_id)

    def skill_id(self, name):
        return self.store.skill_id(name)

    def close(self):
        self.store.close()
