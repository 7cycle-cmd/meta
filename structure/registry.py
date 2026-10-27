# registry.py — structure package 嘅名稱註冊表（已停用）
#
# 2026-10-27：**用戶要求移除 structure 本地 registry 表**。
#    - 唔再 CREATE TABLE registry（唔會自動重建空表）
#    - 唔再寫入（刪咗表之後，寫入會 IntegrityError）
# 名稱註冊（registry）唯一來源 = taxonomy.registry（2026-10-27 rename，
# taxonomy 表改名做 registry）。呢個檔案保留做「8 檔標準」佔位。
#
# 用法（已停用；呼叫會 raise）：
#     from structure.registry import RegistryStore
#     r = RegistryStore()   # -> NotImplementedError

import sqlite3  # noqa: F401

DB_PATH = "C:/projects/meta/structure/structure.db"

_DISABLED_MSG = (
    "structure 本地 registry 表已移除（2026-10-27，用戶要求）。"
    " 名稱註冊請用 taxonomy.registry（from taxonomy import Taxonomy）"
)


class RegistryStore:
    """（已停用）structure 本地名稱註冊

    唔再建表、唔再寫入 —— registry 唯一來源 = taxonomy.registry。
    """

    def __init__(self, db_path=DB_PATH):
        raise NotImplementedError(_DISABLED_MSG)

    def list_registry(self, active_only=True):  # pragma: no cover
        raise NotImplementedError(_DISABLED_MSG)

    def register(self, meta, description=None):  # pragma: no cover
        raise NotImplementedError(_DISABLED_MSG)

    def close(self):  # pragma: no cover
        raise NotImplementedError(_DISABLED_MSG)
