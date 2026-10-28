"""api.py — rule.db 對外 API

rule = 自動化規則層：每個 module 可以註冊自己嘅自動化規則

2026-10-27（用戶要求）：
    registry 表：id | taxonomy_id | flow_id | step_id | parameter
    flow_id / step_id 指 terminology.db（flow 引擎）
    setting 表唔需要（parameter 欄存 JSON）

    add_rule(taxonomy_id, flow_id, step_id, parameter)  登記規則
    rules(taxonomy_id, flow_id)                         列出規則

用法：
    from rule import Rule
    r = Rule()
    r.add_rule(taxonomy_id=1, flow_id=2, step_id=3)
    r.close()
"""

import sqlite3

from .sql import SqlStore


class Rule:
    """自動化規則層（rule.db）嘅對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def add_rule(self, taxonomy_id, flow_id, step_id, parameter=None):
        """登記一條自動化規則（冪等）

        taxonomy_id = taxonomy.registry.id（邊個 module 要自動做嘢）
        flow_id     = terminology.db flow.id（行邊條 flow）
        step_id     = terminology.db step.id（行到邊個 step）
        parameter   = 額外參數（JSON 字串，可選）
        """
        return self.store.add_rule(taxonomy_id, flow_id, step_id, parameter)

    def rules(self, taxonomy_id=None, flow_id=None, active_only=True,
              limit=100):
        """列出規則（可按 module / flow 篩選）"""
        return self.store.rules(taxonomy_id, flow_id, active_only, limit)

    def count(self):
        return self.store.count()

    def close(self):
        self.store.close()