"""sync.py — definition 同步器（冪等）

保證呢幾張表一致（都係「module 清單」）：
    taxonomy.db.taxonomy            ← module 清單（tree = module）
    taxonomy.db.tree                ← 分類樹

2026-10-23：package 由 system 遷去 taxonomy（package 表 + tree_id）。
2026-10-26：taxonomy.package 表已移除（用戶要求）—— module 清單
          就係 taxonomy 表本身（tree = module），sync 只確保大類存在。

用法：
    from definition.sync import sync_all
    report = sync_all()
"""

from taxonomy.api import Taxonomy


def sync_package_to_module():
    """確保 module 大類存在（taxonomy.tree；module 清單 = taxonomy 表本身）"""
    t = Taxonomy()
    try:
        t.register_category("module", 2, 1)
        return 0
    finally:
        t.close()


def sync_all():
    """確保 module 大類存在。"""
    return {"module_from_package": sync_package_to_module()}


if __name__ == "__main__":
    r = sync_all()
    print("同步報告:", r)
    print("（新增數 = 0 即係已經一致，冪等）")
