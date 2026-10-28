"""api.py — plan.db 對外 API

plan = 計劃層：preflight 通過之後先可以 plan

2026-10-27（用戶要求）：
    plan 表：id | preflight_id | role_id | rule_id | tool_id | value_id | run_id
    時機鏈：preflight → plan → schema → task
    2026-10-27b：skill_id → tool_id（工具層話事）
    2026-10-27d：+ role_id（邊個角色落 order，role.db registry 表）
    2026-10-27e：+ rule_id（跟邊條規則，rule.db rule 表；多維度 SSOT）

    add_plan(preflight_id, run_id, role_id, rule_id, tool_id, value_id)  登記一個計劃
    plans(preflight_id, role_id, rule_id, tool_id, value_id)             列出計劃

用法：
    from plan import Plan
    p = Plan()
    p.add_plan(preflight_id=1, run_id=4, role_id=3, rule_id=5,
               tool_id=2, value_id=3)
    p.close()
"""

import sqlite3

from .sql import SqlStore


class Plan:
    """計劃層（plan.db）嘅對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def add_plan(self, preflight_id, run_id, role_id=None, rule_id=None,
                 tool_id=None, value_id=None):
        """登記一個計劃（冪等：preflight_id + run_id 組合）

        preflight_id = preflight.registry.id（起飛前檢查通過咗）
        run_id       = terminology.run.id（全站 flow 引擎產生）
        role_id      = role.db registry.id（邊個角色落 order）
        rule_id      = rule.db rule.id（跟邊條規則）
        tool_id      = tool.registry.id（邊個工具幫手）
        """
        return self.store.add_plan(preflight_id, run_id, role_id, rule_id,
                                   tool_id, value_id)

    def plans(self, preflight_id=None, role_id=None, rule_id=None,
              tool_id=None, value_id=None, active_only=True, limit=100):
        """列出計劃（可按 preflight / role / rule / tool / value 篩選）"""
        return self.store.plans(preflight_id, role_id, rule_id, tool_id,
                                value_id, active_only, limit)

    def count(self):
        return self.store.count()

    def close(self):
        self.store.close()