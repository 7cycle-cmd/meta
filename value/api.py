"""api.py — value.db 對外 API（值資產層 + 拆分 + terminology 授權）"""

from .sql import SqlStore


class Value:
    """值資產（value.db）嘅對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def add(self, value, taxonomy_id=None):
        """新增 / 攞一個值嘅 id（冪等）

        taxonomy_id = taxonomy.registry.id（邊個 module 登記）
        """
        return self.store.add(value, taxonomy_id)

    def get(self, value_id):
        """按 id 攞一個值"""
        return self.store.get(value_id)

    def by_value(self, value):
        """按值攞行（唔存在 None）"""
        return self.store.by_value(value)

    def list(self, taxonomy_id=None, active_only=True):
        """列出值（可按 module 篩選）"""
        return self.store.list(taxonomy_id, active_only)

    # ---------- split（2026-10-28 用戶要求） ----------
    def add_split(self, value_id, parts):
        """拆分一個值（自動寫 split_total + split_value）

        parts = [str, str, ...]（拆出嚟嘅值，次序 = seq）
        返回 {"split_total_id": n, "split_values": [id, ...]}
        """
        return self.store.add_split(value_id, parts)

    def split_totals(self, value_id=None, active_only=True):
        """列出拆分總覽（可按值篩選）"""
        return self.store.split_totals(value_id, active_only)

    def split_values(self, split_total_id=None, value_id=None,
                     active_only=True):
        """列出拆分值（可按拆分 / 值篩選）"""
        return self.store.split_values(split_total_id, value_id, active_only)

    def split_and_prove(self, value, parts, taxonomy_id=None, role_id=None):
        """一站式：value → split → 行 split_value flow → 寫 run（證明）"""
        return self.store.split_and_prove(value, parts, taxonomy_id, role_id)

    # ---------- terminology 授權（2026-10-28 用戶要求） ----------
    def grant_terminology(self, terminology_id, split_value_id):
        """授權一個拆分值有權 call terminology（冪等）"""
        return self.store.grant_terminology(terminology_id, split_value_id)

    def terminology_rows(self, split_value_id=None, active_only=True):
        """列出授權（可按拆分值篩選）"""
        return self.store.terminology_rows(split_value_id, active_only)

    def can_call_terminology(self, split_value_id, terminology_id):
        """一個拆分值有冇權 call terminology"""
        return self.store.can_call_terminology(split_value_id, terminology_id)

    def proof_of(self, value):
        """一個 value 嘅完整證明鏈（值 → 拆分 → 授權 → 身份 → 證明）

        返回 {"value", "found", ...}：
            冇呢個值 -> {"value": value, "found": False}
            有 -> value 行 + split_total + split_value +
                  permit（terminology 授權）+ identity + runs/evidence（terminology）
        """
        return self.store.proof_of(value)

    def count(self):
        return self.store.count()

    def close(self):
        self.store.close()