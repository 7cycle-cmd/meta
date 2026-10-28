"""api.py — resource 對外 API"""

from .sql import SqlStore


class Resource:
    """resource 對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def close(self):
        self.store.close()

    # ---------- resource_schema（2026-10-28 用戶設計） ----------
    def add_resource_schema(self, taxonomy_tree_id, schema_registry_id):
        """登記「module 用 schema」一次使用（冪等，by_id）"""
        return self.store.add_resource_schema(taxonomy_tree_id,
                                              schema_registry_id)

    def list_resource_schemas(self, taxonomy_tree_id=None,
                              schema_registry_id=None, active_only=True):
        """列出 resource_schema（可按 tree / schema registry 篩選）"""
        return self.store.resource_schemas(taxonomy_tree_id,
                                           schema_registry_id,
                                           active_only)

    # ---------- resource_tool（2026-10-28 用戶設計） ----------
    def add_resource_tool(self, taxonomy_tree_id, tool_registry_id):
        """登記「module 用 tool」一次使用（冪等，by_id）"""
        return self.store.add_resource_tool(taxonomy_tree_id,
                                            tool_registry_id)

    def list_resource_tools(self, taxonomy_tree_id=None,
                            tool_registry_id=None, active_only=True):
        """列出 resource_tool（可按 tree / tool registry 篩選）"""
        return self.store.resource_tools(taxonomy_tree_id,
                                         tool_registry_id,
                                         active_only)
