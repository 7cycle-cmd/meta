"""registry.py — ast 嘅名稱註冊表"""

REGISTRY = {
    "ast": "AST 分析 module",
    "Ast": "AST 分析 API 類",
    "SqlStore": "ast.db 存取層",
}


def registry_defs():
    return REGISTRY
