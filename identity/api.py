"""api.py — identity 對外 API（身份層：value × condition × flow × step）"""

from .sql import SqlStore

from .function import *  # noqa: F401,E402


class Identity:
    """身份層：統一管理系統所有身份（value + 證明鏈）"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def register(self, value_id, condition_id, flow_id, step_id,
                 taxonomy_id=None, permit_id=None, description=None):
        """登記一個身份（冪等：value × condition × flow × step）

        value_id     = value.db value.id（身份主檔）
        condition_id = terminology.condition.id（判斷）
        flow_id      = terminology.flow.id（證明 flow）
        step_id      = terminology.step.id（證明步驟）
        permit_id    = permit.db permit.id（授權，可選）
        """
        return self.store.register(value_id, condition_id, flow_id, step_id,
                                   taxonomy_id, permit_id, description)

    def lookup(self, value_id, condition_id=None, flow_id=None, step_id=None):
        """按 value（+ condition/flow/step 可選）攞身份"""
        rows = self.store.lookup(value_id, condition_id, flow_id, step_id)
        return [dict(r) for r in rows]

    def resolve(self, value_id, condition_id, flow_id, step_id):
        """由 value + condition + flow + step 攞身份（冇 = None）"""
        r = self.store.resolve(value_id, condition_id, flow_id, step_id)
        return dict(r) if r else None

    def list_all(self, value_id=None, flow_id=None, active_only=True):
        """列出全部身份（可按 value / flow 篩選）"""
        return self.store.lookup_all(value_id, flow_id, active_only)

    def close(self):
        self.store.close()
