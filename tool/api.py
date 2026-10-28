"""api.py — tool.db 對外 API

tool = 工具層：一個 mission 可以攞到邊個工具幫手（by REST_API_id）

2026-10-27（用戶要求）：
    registry 表：id | module_id | skill_id | REST_API_WRITE_id | REST_API_READ_id
    READ 中心 = monitor（rest_api_READ）
    WRITE 中心 = tool（rest_api_WRITE）

    add_write_api(module_id, rest_api)  登記 WRITE API（WRITE 中心）
    write_apis(module_id)               列出 WRITE API
    add_tool(module_id, skill_id, rest_api_write_id, rest_api_read_id)  登記工具
    tools(module_id, skill_id)                                          列出工具
    tools_for_mission(module_id, skill_id)                              攞工具幫手

用法：
    from tool import Tool
    t = Tool()
    t.add_tool(module_id=1, skill_id=2, rest_api_write_id=3, rest_api_read_id=4)
    t.close()
"""

import sqlite3

from .sql import SqlStore


class Tool:
    """工具層（tool.db）嘅對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    # ---------- WRITE 中心 ----------
    def add_write_api(self, module_id, rest_api):
        """登記一個 WRITE API（冪等：module_id + rest_api 組合）"""
        return self.store.add_write_api(module_id, rest_api)

    def write_apis(self, module_id=None, active_only=True):
        """列出 WRITE API 中心（可按 module 篩選）"""
        return self.store.write_apis(module_id, active_only)

    # ---------- 工具 ----------
    def add_tool(self, module_id, skill_id=None, rest_api_write_id=None,
                 rest_api_read_id=None):
        """登記一個工具（冪等）

        module_id         = taxonomy.registry.id（邊個 module 擁有）
        skill_id          = skill.registry.id（邊個技能）
        rest_api_write_id = tool.rest_api_WRITE.id（WRITE API）
        rest_api_read_id  = monitor.rest_api_READ.id（READ API）
        """
        return self.store.add_tool(module_id, skill_id, rest_api_write_id,
                                   rest_api_read_id)

    def tools(self, module_id=None, skill_id=None, active_only=True,
              limit=100):
        """列出工具（可按 module / skill 篩選）"""
        return self.store.tools(module_id, skill_id, active_only, limit)

    def tools_for_mission(self, module_id=None, skill_id=None):
        """一個 mission 可以攞到邊個工具幫手（by REST_API_id）

        返回工具清單（含 READ + WRITE API id）
        """
        return self.store.tools(module_id, skill_id)

    def count(self):
        return self.store.count()

    def close(self):
        self.store.close()