"""skill registry 同 module-skill 關聯嘅對外 API。"""

from .sql import SqlStore


class Skill:
    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def registry(self, module_id=None):
        return self.store.registry(module_id)

    def register(self, module_id, value):
        return self.store.register(module_id, value)

    def module_skills(self, skill_id=None):
        return self.store.module_skills(skill_id)

    def link(self, skill_id, flow_id, value_id):
        return self.store.link(skill_id, flow_id, value_id)

    def close(self):
        self.store.close()
