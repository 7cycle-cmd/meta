"""api.py — taxonomy.db 對外 API"""

from .sql import SqlStore


class Taxonomy:
    """分類學（taxonomy.db）嘅對外介面：tree / registry"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    # ---------- physical_path（實體路徑鏈，2026-10-26） ----------
    def list_physical_paths(self, module=None):
        """列出實體路徑鏈（可按 module 篩選）"""
        return self.store.physical_paths(module)

    # ---------- 分類樹（tree 表）----------
    def list_categories(self, active_only=False):
        """列出全部大類（tree）"""
        return self.store.categories(active_only)

    def register_category(self, meta_key, seq, is_active=0):
        """登記一個大類（tree）"""
        return self.store.insert_category(meta_key, seq, is_active)

    def deactivate_category(self, category_id):
        """停用一個大類（tree）"""
        return self.store.deactivate_category(category_id)

    # ---------- 分類項目（registry 表，2026-10-27 由 taxonomy 改名）----------
    def list_items(self, tree=None, active_only=True):
        """列出分類項目（可按 tree 名篩選：channel / module / skill）"""
        return self.store.items(tree, active_only)

    def register_item(self, tree, meta, is_active=1):
        """登記一個分類項目（已存在就更新 is_active）"""
        return self.store.insert_item(tree, meta, is_active)

    def deactivate_item(self, item_id):
        """停用一個分類項目（soft delete）"""
        return self.store.deactivate_item(item_id)

    def delete_item(self, item_id):
        """真正移除一個分類項目"""
        return self.store.delete_item(item_id)

    # ---------- module（registry 表，tree = module）----------
    def list_modules(self, active_only=True):
        """列出全部 module（registry 表，tree = module）"""
        return self.store.items("module", active_only)

    def register_module(self, meta):
        """登記一個 module（registry 表，tree = module）"""
        return self.store.insert_item("module", meta)

    def sync_modules_from_registry(self):
        """由 resource.db registry 匯入缺嘅 module（經 API）"""
        return self.store.sync_items_from_registry()

    # ---------- skill（registry 表，tree = skill）----------
    def list_skills(self, active_only=True):
        """列出全部 skill（registry 表，tree = skill）"""
        return self.store.items("skill", active_only)

    def register_skill(self, meta, is_active=1):
        """登記一個 skill（registry 表，tree = skill）"""
        return self.store.insert_item("skill", meta, is_active)

    def deactivate_skill(self, item_id):
        """停用一個 skill"""
        return self.store.deactivate_item(item_id)

    # ---------- channel（registry 表，tree = channel）----------
    def list_channels(self, active_only=True):
        """列出全部 channel（registry 表，tree = channel）"""
        return self.store.items("channel", active_only)

    def register_channel(self, meta, is_active=1):
        """登記一個 channel（registry 表，tree = channel）"""
        return self.store.insert_item("channel", meta, is_active)

    def deactivate_channel(self, item_id):
        """停用一個 channel"""
        return self.store.deactivate_item(item_id)

    def close(self):
        self.store.close()
