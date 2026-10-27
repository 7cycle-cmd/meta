"""function.py — source 核心業務邏輯層

呢個 module 嘅核心邏輯全部喺 api.py class 方法內（真實業務邏輯）：

    Source: list_sources, get, lookup, register, update, deactivate, count, list_authority_levels, get_authority_level, lookup_authority_level, authority_level_by_value, list_providers, get_provider, lookup_provider, register_provider, register_provider_by_industry, update_provider, deactivate_provider, count_providers, list_industries, get_industry, lookup_industry, register_industry, update_industry, deactivate_industry, count_industries

（7 檔標準：__init__/function/api/route/schema/sql/skill 全部 required）
呢個檔案係業務邏輯嘅「統一入口標記」—— class 方法 = 業務邏輯，
api.py 係對外介面；function.py 係邏輯清單。
"""
