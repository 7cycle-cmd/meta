"""api.py — task.db 對外 API

task = 任務層：preflight + schema 都通過之後先可以 task

2026-10-27（用戶要求）：
    task 表：id | preflight_id | schema_id | plan_id | role_id | rule_id | tool_id | value_id | run_id
    時機鏈：preflight → plan → schema → task
    2026-10-27b：skill_id → tool_id（工具層話事）
    2026-10-27c：+ plan_id（呢個 task 跟邊個 plan）
    2026-10-27d：+ role_id（邊個角色執行，role.db registry 表）
    2026-10-27e：+ rule_id（跟邊條規則，rule.db rule 表；多維度 SSOT）

    add_task(preflight_id, schema_id, run_id, plan_id, role_id, rule_id, tool_id, value_id)  登記一個任務
    tasks(preflight_id, schema_id, plan_id, role_id, rule_id, tool_id, value_id)             列出任務

用法：
    from task import Task
    t = Task()
    t.add_task(preflight_id=1, schema_id=2, run_id=5, plan_id=3,
               role_id=4, rule_id=5, tool_id=5, value_id=6)
    t.close()
"""

import sqlite3

from .sql import SqlStore


class Task:
    """任務層（task.db）嘅對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def add_task(self, preflight_id, schema_id, run_id, plan_id=None,
                 role_id=None, rule_id=None, tool_id=None, value_id=None):
        """登記一個任務（冪等：preflight_id + schema_id + run_id 組合）

        preflight_id = preflight.registry.id（起飛前檢查通過咗）
        schema_id    = schema.registry.id（執行前檢查通過咗）
        run_id       = terminology.run.id（全站 flow 引擎產生）
        plan_id      = plan.id（跟邊個 plan）
        role_id      = role.db registry.id（邊個角色執行）
        rule_id      = rule.db rule.id（跟邊條規則）
        tool_id      = tool.registry.id（邊個工具幫手）
        """
        return self.store.add_task(preflight_id, schema_id, run_id,
                                   plan_id, role_id, rule_id, tool_id,
                                   value_id)

    def tasks(self, preflight_id=None, schema_id=None, plan_id=None,
              role_id=None, rule_id=None, tool_id=None, value_id=None,
              active_only=True, limit=100):
        """列出任務（可按 preflight / schema / plan / role / rule / tool / value 篩選）"""
        return self.store.tasks(preflight_id, schema_id, plan_id, role_id,
                                rule_id, tool_id, value_id, active_only,
                                limit)

    def count(self):
        return self.store.count()

    def close(self):
        self.store.close()