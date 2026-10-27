"""api.py — common.db 對外 API（中央字典）"""

from .sql import SqlStore


class Common:
    """中央字典（common.db）嘅對外介面：action / status

    所有 module 由呢度攞 action_id / status_id，唔使喺自己 DB 建表。
    """

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    # ---------- action ----------
    def list_actions(self, active_only=True):
        """列出全部動作字典"""
        return self.store.actions(active_only)

    def get_action(self, meta):
        return self.store.action(meta)

    def action_id(self, meta):
        """由動作名攞 id（例如 "DROP" -> 1）"""
        return self.store.action_id(meta)

    def register_action(self, meta):
        """登記一個動作（冪等）"""
        return self.store.add_action(meta)

    # ---------- status ----------
    def list_statuses(self, active_only=True):
        """列出全部狀態字典"""
        return self.store.statuses(active_only)

    def get_status(self, meta):
        return self.store.status(meta)

    def status_id(self, meta):
        """由狀態名攞 id（例如 "active" -> 4）"""
        return self.store.status_id(meta)

    def register_status(self, meta):
        """登記一個狀態（冪等）"""
        return self.store.add_status(meta)

    # ---------- role（角色字典：guard 寫入證明用） ----------
    def list_roles(self, active_only=True):
        """列出全部角色字典"""
        return self.store.roles(active_only)

    def get_role(self, meta):
        return self.store.role(meta)

    def role_id(self, meta):
        """由角色名攞 id（例如 "worker" -> 2）"""
        return self.store.role_id(meta)

    def register_role(self, meta):
        """登記一個角色（冪等）"""
        return self.store.add_role(meta)

    # ---------- seq（位置字典：跨 module 共用；2026-10-27 position -> seq） ----------
    def list_seqs(self, active_only=True):
        """列出全部 seq 字典（1-100）"""
        return self.store.seqs(active_only)

    def get_seq(self, meta):
        return self.store.seq(meta)

    def get_seq_by_value(self, value):
        """由數值攞 seq（例如 10）"""
        return self.store.seq_by_value(value)

    def seq_id(self, meta):
        """由位置名攞 id（例如 "1" -> 1）；唔存在自動登記（冪等）"""
        return self.store.seq_id(meta)

    def register_seq(self, meta, value=None):
        """登記一個位置（冪等）"""
        return self.store.add_seq(meta, value)

    # ---------- position（兼容 alias；表已改名 seq） ----------
    def list_positions(self, active_only=True):
        return self.store.positions(active_only)

    def get_position(self, meta):
        return self.store.position(meta)

    def get_position_by_value(self, value):
        return self.store.position_by_value(value)

    def position_id(self, meta):
        return self.store.position_id(meta)

    def register_position(self, meta, value=None):
        return self.store.add_position(meta, value)

    # ---------- boolean（布林字典：value 只有 0 / 1） ----------
    def list_booleans(self, active_only=True):
        """列出布林字典（boolean：value 0 / 1）"""
        return self.store.booleans(active_only)

    def get_boolean(self, value):
        """由值攞 boolean（0 / 1）"""
        return self.store.boolean_by_value(value)

    def boolean_id(self, value):
        """由值攞 id（0/1）"""
        return self.store.boolean_id(value)

    # ---------- resource_action（資源 × 正確動作選項） ----------
    def list_resource_actions(self, resource_id=None, ontology_id=None,
                              filling_id=None):
        """列出資源嘅正確動作選項（可按 resource / ontology / filling 篩選）"""
        return self.store.resource_actions(resource_id, ontology_id, filling_id)

    def set_resource_action(self, resource_id, action_id, ontology_id=None,
                            filling_id=None):
        """設定一個資源嘅正確動作（冪等 upsert）"""
        return self.store.set_resource_action(resource_id, action_id,
                                              ontology_id, filling_id)

    def resource_action_ids(self, resource_id, ontology_id=None,
                            filling_id=None):
        """攞一個資源所有正確 action_id 清單（option 用）"""
        rows = self.store.resource_actions(resource_id, ontology_id, filling_id)
        return [r["action_id"] for r in rows]

    def clear_resource_actions(self, resource_id):
        """清走一個資源嘅動作選項"""
        return self.store.clear_resource_actions(resource_id)

    # ---------- resource_status（資源 × 正確狀態選項） ----------
    def list_resource_statuses(self, resource_id=None, ontology_id=None,
                               filling_id=None):
        """列出資源嘅正確狀態選項（可按 resource / ontology / filling 篩選）"""
        return self.store.resource_statuses(resource_id, ontology_id, filling_id)

    def set_resource_status(self, resource_id, status_id, ontology_id=None,
                             filling_id=None):
        """設定一個資源嘅正確狀態（冪等 upsert）"""
        return self.store.set_resource_status(resource_id, status_id,
                                              ontology_id, filling_id)

    def resource_status_ids(self, resource_id, ontology_id=None,
                            filling_id=None):
        """攞一個資源所有正確 status_id 清單（option 用）"""
        rows = self.store.resource_statuses(resource_id, ontology_id, filling_id)
        return [r["status_id"] for r in rows]

    def clear_resource_statuses(self, resource_id):
        """清走一個資源嘅狀態選項"""
        return self.store.clear_resource_statuses(resource_id)

    # ---------- sweep_activity（資源清理活動記錄，中央） ----------
    def list_sweep_activities(self, resource_id=None, action_id=None,
                              type_id=None, sweep_id=None, limit=100):
        """列出清理活動（可按 resource / action / type / sweep_id 篩選）"""
        return self.store.sweep_activities(resource_id, action_id, type_id,
                                           sweep_id, limit)

    def record_sweep_activity(self, resource_id, type_id, action_id,
                              sweep_id=None):
        """記錄一次清理活動（DROP / KEEP / RENAME ...）"""
        return self.store.insert_sweep_activity(resource_id, type_id,
                                                action_id, sweep_id)

    def sweep_activity_count(self):
        return self.store.sweep_activity_count()

    # ---------- migration_activity（資源遷移活動記錄，中央） ----------
    def list_migration_activities(self, resource_id=None, action_id=None,
                                  status_id=None, migration_id=None,
                                  limit=100):
        """列出遷移活動（可按 resource / action / status / migration 篩選）"""
        return self.store.migration_activities(resource_id, action_id,
                                               status_id, migration_id, limit)

    def record_migration_activity(self, resource_id, action_id, status_id,
                                  resource_type_id=None, migration_id=None):
        """記錄一次遷移活動（proof migration 真係做咗）"""
        return self.store.insert_migration_activity(
            resource_id, action_id, status_id, resource_type_id, migration_id)

    def migration_activity_count(self):
        return self.store.migration_activity_count()

    # ---------- token（2026-10-26 用戶設計） ----------
    def add_token(self, token_id, module_id, role_id, file_id=None):
        """登記一個寫入 token（冪等）"""
        return self.store.add_token(token_id, module_id, role_id, file_id)

    def token_id_of(self, token_id, active_only=True):
        """攞 token 行 id（唔存在返回 None）"""
        return self.store.token_id_of(token_id, active_only)

    def valid_token(self, token_id, active_only=True):
        """驗證 token 有冇效（存在 + active）"""
        return self.store.valid_token(token_id, active_only)

    def tokens(self, active_only=True):
        """列出全部 token"""
        return self.store.tokens(active_only)

    def close(self):
        self.store.close()
