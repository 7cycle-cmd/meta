# registry.py — taxonomy package 嘅名稱註冊表（已停用）
#
# 2026-10-27：**registry 表名已被分類項目表佔用**（taxonomy 表改名做
# registry，2026-10-27 用戶要求）—— 呢個舊「meta UNIQUE」註冊表檔案
# 唔再適用（一 CREATE 就會撞新表）。名稱註冊嘅唯一來源 = taxonomy.registry
# （分類項目表，tree_id + meta）。檔案保留做「8 檔標準」佔位。
#
# 用法（已停用；呼叫會 raise）：
#     from taxonomy.registry import RegistryStore
#     r = RegistryStore()   # -> NotImplementedError

import sqlite3  # noqa: F401

DB_PATH = "C:/projects/meta/taxonomy/taxonomy.db"

_DISABLED_MSG = (
    "taxonomy.registry 舊檔案已停用（2026-10-27）—— registry 表名已由"
    " 分類項目表（taxonomy rename）佔用。請用 Taxonomy API"
    "（from taxonomy import Taxonomy）"
)


class RegistryStore:
    """（已停用）舊 registry 註冊表

    registry 表名已由分類項目表佔用（2026-10-27 taxonomy rename），
    唔再建表、唔再寫入。
    """

    def __init__(self, db_path=DB_PATH):
        raise NotImplementedError(_DISABLED_MSG)

    def list_registry(self, active_only=True):  # pragma: no cover
        raise NotImplementedError(_DISABLED_MSG)

    def register(self, meta, description=None):  # pragma: no cover
        raise NotImplementedError(_DISABLED_MSG)

    def close(self):  # pragma: no cover
        raise NotImplementedError(_DISABLED_MSG)
