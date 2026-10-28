"""api.py — role.db 對外 API

role = 角色層：CQRS 身份（邊個 module 以咩角色做嘢）

2026-10-27（用戶要求）：
    module : rule -> rename -> role
    remove -> table : role and rule
    table : registry + taxonomy_id

    add_role(taxonomy_id, meta)  登記角色
    roles(taxonomy_id)           列出角色
    role_id(taxonomy_id, meta)   由 module + 名攞 id

用法：
    from role import Role
    r = Role()
    r.add_role(taxonomy_id=1, meta="owner")
    r.close()
"""

import sqlite3

from .sql import SqlStore


class Role:
    """角色層（role.db）嘅對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def add_role(self, taxonomy_id, meta):
        """登記一個角色（冪等）

        taxonomy_id = taxonomy.registry.id（邊個 module 擁有）
        meta        = 角色名（owner / reader / orderer / recorder ...）
        """
        return self.store.add_role(taxonomy_id, meta)

    def role_id(self, taxonomy_id, meta):
        """由 module + 角色名攞 id（唔存在 None）"""
        return self.store.role_id(taxonomy_id, meta)

    def roles(self, taxonomy_id=None, active_only=True):
        """列出角色（可按 module 篩選）"""
        return self.store.roles(taxonomy_id, active_only)

    def count(self):
        return self.store.count()

    def close(self):
        self.store.close()