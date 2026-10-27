"""skill.py — ast 嘅 skill 定義

AST 分析嘅技能：AST 解析、function 抽取、analyze 寫入。
"""

SKILLS = [
    ("ast_parse", "AST 解析 .py 檔"),
    ("function_extract", "抽出 function / class"),
    ("analyze_write", "寫入 analyze 表"),
]


def skill_defs():
    return SKILLS
