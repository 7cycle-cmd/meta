"""api.py — register.db 對外 API（註冊層）

register = 執行規則（rule）→ 寫入註冊結果。
sync_rest_apis()：讀 rule.db 規則 -> 掃 module/rest_api.py -> 寫入 register.db。
"""

import os
import re

from .sql import SqlStore

META_ROOT = r"C:\projects\meta"


class Register:
    """註冊（register.db）嘅對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    # ---------- REST API 註冊 ----------
    def list_rest_apis(self, module=None, type=None):
        """列出 REST API 註冊"""
        return self.store.rest_apis(module, type)

    def sync_rest_apis(self, module=None):
        """自動註冊 REST API（自己掃 module/rest_api.py）

        2026-10-27：rule module 已 rename 做 role（registry + taxonomy_id）——
        register 自己掃 module/rest_api.py（唔經 rule）。

        返回 {"registered": n, "modules": n, "skipped": [...]}
        """
        modules = [
            d for d in os.listdir(META_ROOT)
            if os.path.isdir(os.path.join(META_ROOT, d))
            and os.path.exists(os.path.join(META_ROOT, d, "rest_api.py"))
        ]
        if module:
            modules = [m for m in modules if m == module]
        n = 0
        skipped = []
        for mod in sorted(modules):
            rap = os.path.join(META_ROOT, mod, "rest_api.py")
            try:
                txt = open(rap, encoding="utf-8", errors="ignore").read()
            except Exception as e:
                skipped.append(f"{mod}: 讀唔到（{e}）")
                continue
            found = set()
            for m in re.finditer(
                    r'path\s*==\s*["\'](/[A-Za-z0-9_\-]*)["\']', txt):
                api = m.group(1)
                if api in ("/health", ""):
                    continue
                found.add(api)
            for api in sorted(found):
                self.store.add_rest_api(mod, "READ", api)
                n += 1
        return {"registered": n, "modules": len(modules),
                "skipped": skipped}

    def reset(self, module=None):
        """清空註冊（重新 sync）"""
        return self.store.reset(module)

    def count(self):
        return self.store.count()

    def close(self):
        self.store.close()
