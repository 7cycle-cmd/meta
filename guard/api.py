"""api.py — guard.db 對外 API（token registry 守衛）"""

from .sql import SqlStore


class Guard:
    """寫入憑證守衛（guard.db registry）嘅對外介面

    2026-10-26 重建：守衛只存在於 rest_api（HTTP 入口）。
    registry = token 登記表（rest_api 驗證 ?token=/X-API-Token）。

    用法：
        from guard import Guard
        g = Guard()
        g.register_token('terminology.api', module_id=4)
        g.valid_token('terminology.api')   # True / False
        g.close()
    """

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def register(self, token_id, module_id, file_id=None):
        """登記一個 token（冪等）"""
        return self.store.register_token(token_id, module_id, file_id)

    def register_many(self, items):
        """一次過登記多個 token [(token_id, module_id), ...]"""
        return self.store.register_many(items)

    def valid(self, token_id, active_only=True):
        """驗證 token 有冇效（存在 + is_active=1）"""
        return self.store.valid_token(token_id, active_only)

    def token_row(self, token_id, active_only=True):
        """攞 token 行"""
        return self.store.token_row(token_id, active_only)

    def tokens(self, active_only=True):
        """列出全部 token"""
        return self.store.tokens(active_only)

    # ---------- permit 接入（2026-10-28：授權檢查） ----------
    def check_permit(self, token_id, permit_type, object, object_type):
        """檢查：token（module）對 object 有冇 permit（permit.db 權威）

        流程：
            1. token 有效？（guard.db registry）
            2. token -> module_id（taxonomy 對應）
            3. permit.db：module.<meta>（module 類型 subject）有冇
               permit_type + object 嘅授權

        返回 {"allowed": bool, "reason": str, "module": str|None}
        """
        # 1. token 有效
        if not self.valid(token_id):
            return {"allowed": False, "reason": f"token '{token_id}' 無效",
                    "module": None}
        # 2. token -> module_id
        rows = self.token_row(token_id)
        if not rows:
            return {"allowed": False, "reason": f"token '{token_id}' 冇登記",
                    "module": None}
        module_id = rows[0]["module_id"]
        # module_id -> module meta（taxonomy.db）
        module_meta = None
        try:
            import sqlite3
            tc = sqlite3.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
            tc.row_factory = sqlite3.Row
            try:
                m = tc.execute(
                    "SELECT meta FROM registry WHERE id = ? AND is_active = 1",
                    (module_id,)).fetchone()
                module_meta = m["meta"] if m else None
            finally:
                tc.close()
        except Exception:
            module_meta = None
        if not module_meta:
            return {"allowed": False, "reason": f"module_id={module_id} 唔存在",
                    "module": None}
        # 3. permit.db 檢查
        try:
            from permit import Permit
            pm = Permit()
            try:
                ok = pm.can(f"module.{module_meta}", "module",
                            permit_type, object, object_type)
            finally:
                pm.close()
        except Exception as e:
            return {"allowed": False, "reason": f"permit 查詢失敗：{e}",
                    "module": module_meta}
        return {"allowed": ok,
                "reason": (f"{module_meta} {permit_type} {object} 有權"
                           if ok else
                           f"{module_meta} {permit_type} {object} 冇權（permit 冇）"),
                "module": module_meta}

    def count(self):
        return self.store.count()

    def close(self):
        self.store.close()
