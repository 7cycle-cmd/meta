"""function.py — resource 核心業務邏輯層

（8 檔標準：__init__/function/api/route/schema/sql/registry/rest_api 全部 required）
核心邏輯喺 api.py resource.api 類方法內。

2026-10-28（用戶設計）：
    resource_schema  id | taxonomy.tree_id | schema.registry_id
    resource_tool    id | taxonomy.tree_id | tool.registry_id
    add = 登記一次使用（冪等，by_id）；list = 篩選查詢。
"""
