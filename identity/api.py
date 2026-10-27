"""api.py — identity 對外 API（身份層：名字 → id 對應）"""

from .sql import SqlStore, KINDS

from .function import *  # noqa: F401,E402


class Identity:
    """身份層：統一管理系統所有名字嘅唯一 id"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def register(self, kind, name, ref_id=None, description=None,
                 taxonomy_id=None, resource_id=None):
        """登記一個身份（package/skill/flow/step/module）

        taxonomy_id / resource_id：選填，對應 taxonomy.db / resource.db
        """
        return self.store.register(kind, name, ref_id, description,
                                   taxonomy_id, resource_id)

    def lookup(self, kind, name):
        """按 kind + name 攞 id（例如 lookup('package', 'codegen')）"""
        r = self.store.lookup(kind, name)
        return dict(r) if r else None

    def resolve(self, kind, name_or_id):
        """由名或 id 攞身份"""
        r = self.store.resolve(kind, name_or_id)
        return dict(r) if r else None

    def list_all(self, kind=None):
        """列出全部身份（可按 kind 篩選）"""
        return self.store.lookup_all(kind)

    def list_kinds(self):
        """列出所有已用嘅 kind"""
        return self.store.kinds()

    def close(self):
        self.store.close()
