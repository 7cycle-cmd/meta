"""function.py — taxonomy 核心業務邏輯層

呢個 module 嘅核心邏輯全部喺 api.py class 方法內（真實業務邏輯）：

    Taxonomy: list_categories, register_category, deactivate_category, list_items, register_item, deactivate_item, delete_item, list_modules, register_module, sync_modules_from_registry, list_skills, register_skill, deactivate_skill, list_channels, register_channel, deactivate_channel
    tree 只剩 channel / module / skill。

（8 檔標準：__init__/function/api/route/schema/sql/registry/rest_api 全部 required）
呢個檔案係業務邏輯嘅「統一入口標記」—— class 方法 = 業務邏輯，
api.py 係對外介面；function.py 係邏輯清單。
"""
