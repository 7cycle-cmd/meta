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

    def count(self):
        return self.store.count()

    def close(self):
        self.store.close()