"""function.py — terminology 核心業務邏輯層

呢個 module 嘅核心邏輯全部喺 api.py class 方法內（真實業務邏輯）：

    Terminology: list_terms, get, lookup, register, update, deactivate, count

（7 檔標準：__init__/function/api/route/schema/sql/skill 全部 required）
呢個檔案係業務邏輯嘅「統一入口標記」—— class 方法 = 業務邏輯，
api.py 係對外介面；function.py 係邏輯清單。
"""
