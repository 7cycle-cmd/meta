"""registry.py — migration 註冊（taxonomy module tree）

migration module 要喺 taxonomy 註冊（tree_id=2 module）先可以
被其他 module 識別做「taxonomy_id」。冪等。
"""

import sqlite3

DB_PATH = r"C:\projects\meta\taxonomy\taxonomy.db"


def register():
    """確保 migration module 喺 taxonomy 登記（冪等）"""
    c = sqlite3.connect(DB_PATH)
    try:
        c.row_factory = sqlite3.Row
        # tree_id=2 = module
        has = c.execute(
            "SELECT id FROM registry WHERE meta = 'migration'"
            " AND tree_id = 2 AND is_active = 1").fetchone()
        if not has:
            c.execute(
                "INSERT INTO registry (tree_id, meta)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM registry WHERE meta = ? AND tree_id = 2)",
                (2, "migration", "migration"))
            c.commit()
            print("[migration] registry 註冊完成")
        return True
    finally:
        c.close()


if __name__ == "__main__":
    register()
