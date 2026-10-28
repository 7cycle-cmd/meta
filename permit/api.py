"""api.py — permit.db 對外 API（授權模型）"""

from .sql import SqlStore


class Permit:
    """授權（permit.db）嘅對外介面

    模型：permit = subject × permit × object
    """

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def add_permit(self, subject, subject_type, permit_type, object,
                   object_type):
        """授權（冪等）

        subject      = 主體識別（例如 value.split_value.1）
        subject_type = module / split_value / worker / tool ...
        permit_type  = call / read / write / run / order / record ...
        object       = 目標識別（例如 terminology.word_proof）
        object_type  = terminology / rest_api / flow / step / value ...
        """
        return self.store.add_permit(subject, subject_type, permit_type,
                                     object, object_type)

    def can(self, subject, subject_type, permit_type, object, object_type):
        """檢查：subject 對 object 有冇 permit"""
        return self.store.can(subject, subject_type, permit_type,
                              object, object_type)

    def permits(self, subject=None, permit_type=None, object=None,
                active_only=True, limit=200):
        """列出授權"""
        return self.store.permits(subject, permit_type, object,
                                  active_only, limit)

    def subjects(self, subject_type=None, active_only=True):
        """列出主體"""
        return self.store.subjects(subject_type, active_only)

    def objects(self, object_type=None, active_only=True):
        """列出目標"""
        return self.store.objects(object_type, active_only)

    # ---------- import permit（2026-10-28 用戶：worker 唔可以靠 import 逃工）----------
    def check_import_permit(self, module_name, imported, symbols="*"):
        """檢查 module 有冇權 import（allowlist 之外 = 擋）"""
        return self.store.check_import_permit(module_name, imported, symbols)

    # ---------- import 申請（2026-10-28 用戶：按 need，冇 default）----------
    def request_import(self, module_name, imported, symbols="ALL",
                       reason=None, tool_id=None):
        """module 申請 import（-> pending，等 tool/monitor 批）"""
        return self.store.request_import(module_name, imported, symbols,
                                          reason, tool_id)

    def approve_import(self, request_id, decided_by="tool",
                       condition_id=None, flow_id=None, step_id=None,
                       question_id=None, expected_source_id=None):
        """批准申請（-> import_permit 正式授權，帶證明鏈）

        證明鏈：function = condition × 5W2H × operator × expected
        expected_source_id = 解釋「點解可以批 permit」
        """
        return self.store.approve_import(
            request_id, decided_by, condition_id, flow_id, step_id,
            question_id, expected_source_id)

    def reject_import(self, request_id, decided_by="tool"):
        """拒絕申請"""
        return self.store.reject_import(request_id, decided_by)

    def import_requests(self, module_name=None, status=None):
        """列出申請"""
        return self.store.import_requests(module_name, status)

    def register_import(self, module_name, imported, symbols="*"):
        """登記 import（冇 permit 會 raise PermissionError）"""
        return self.store.register_import(module_name, imported, symbols)

    def imports(self, module_name=None, active_only=True):
        """列出 import_registry"""
        return self.store.imports(module_name, active_only)

    def import_permits(self, active_only=True):
        """列出 import_permit allowlist"""
        return self.store.import_permits(active_only)

    def count(self):
        return self.store.count()

    def close(self):
        self.store.close()