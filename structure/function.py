"""function.py — structure 核心業務邏輯（由 api.py / sql.py 抽離）

structure 嘅業務邏輯層：
    _migrate_type_to_db_field_type()  舊表 type -> column_type -> db_field_type
    _migrate_table_type_to_db_table_type()  舊表 table_type -> db_table_type
    _infer_field_pattern()            由 SQL 型別 + 約束推 db_field_setting pattern 名
    build_column_definitions()        由 db_table_setting 組 DDL column_definitions 字串

sql.py（存取層）只負責 SQL 執行；api.py（介面）只負責對外方法。
呢度先係「點樣由設定砌出真實 DDL」嘅邏輯本體。
"""


def _migrate_type_to_db_field_type(conn):
    """自動遷移：舊表 type -> column_type -> db_field_type（如果仲存在舊名）"""
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")]
    if "type" in tables and "column_type" not in tables:
        conn.execute("ALTER TABLE type RENAME TO column_type")
        conn.commit()
    if "column_type" in tables and "db_field_type" not in tables:
        conn.execute("ALTER TABLE column_type RENAME TO db_field_type")
        conn.commit()


def _migrate_table_type_to_db_table_type(conn):
    """自動遷移：舊表 table_type / db_table_type 都唔需要（概念已移除）

    2026-10-23：db_table_type 概念移除——表名就係表。
    舊表存在就刪（冇用途）。
    """
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")]
    for name in ("db_table_type", "table_type"):
        if name in tables:
            conn.execute(f"DROP TABLE IF EXISTS {name}")
    conn.commit()


# SQL 型別 -> db_field_setting pattern 名（由真表 PRAGMA 推導，唔硬編碼 id）
# 2026-10-22：pattern 名要同 structure.db db_field_setting.meta 一致
FIELD_PATTERN_BY_SQL = {
    # (type, not_null, pk, auto, unique)
    ("INTEGER", 1, 1, 1, 0): "int_required_pk_unique_auto",
    ("INTEGER", 1, 0, 0, 0): "int_required",
    ("INTEGER", 0, 0, 0, 1): "int_optional_unique",
    ("TEXT", 1, 0, 0, 1): "text_required_unique",
    ("TEXT", 1, 0, 0, 0): "text_required",
    ("TEXT", 0, 0, 0, 1): "text_optional_unique",
    ("TEXT", 0, 0, 0, 0): "text_optional",
    ("BOOLEAN", 1, 0, 0, 0): "bool_required",
    ("BOOLEAN", 0, 0, 0, 0): "bool_optional",
    ("REAL", 1, 0, 0, 0): "real_required",
    ("REAL", 0, 0, 0, 0): "real_optional",
    ("DATETIME", 1, 0, 0, 0): "datetime_required",
    ("DATETIME", 0, 0, 0, 0): "datetime_optional",
}


def infer_field_pattern(sql_type, not_null=0, is_pk=0, auto=0, unique=0):
    """由 SQL 型別 + 約束推 db_field_setting pattern 名

    唔識嘅組合 -> None（caller 自己決定，唔好用 0 冒充）
    """
    return FIELD_PATTERN_BY_SQL.get((sql_type, int(not_null), int(is_pk),
                                     int(auto), int(unique)))


def build_column_definitions(settings):
    """由 db_table_setting 列表組 column_definitions 字串（生成 CREATE TABLE）

    settings = [dict]：
        meta_key             欄位名（必需）
        type_name            型別名（TEXT / INTEGER / ...，必需）
        not_null / is_pk / auto_increment / unique
        references_table     同 DB 嘅 FK 目標表（可選）
        references_column    同 DB 嘅 FK 目標欄位（可選）
        check_expr           自訂 CHECK 表達式（可選，{col} = 欄位名）
        default_value        預設值（可選；含括號/函數會自動包括號）

    返回 "col1 INTEGER NOT NULL, col2 TEXT, ..."

    2026-10-24：加 default_value + 欄位名引號（數字開頭欄位名要 "5w2h_id"）。
    """
    parts = []
    for s in settings:
        name = s.get("meta_key") or s.get("name")
        if not name:
            continue
        t = s.get("type_name") or s.get("data_type") or "TEXT"
        # 數字開頭 / 特殊字符欄位名 -> 加引號（5w2h_id）
        if name[0].isdigit() or not name.replace("_", "").isalnum():
            name = f'"{name}"'
        bits = [name, t]
        if s.get("is_pk"):
            bits.append("PRIMARY KEY")
        if s.get("auto_increment"):
            bits.append("AUTOINCREMENT")
        if s.get("not_null") and not s.get("is_pk"):
            # INTEGER PRIMARY KEY 已隱含 NOT NULL，唔可以再加
            bits.append("NOT NULL")
        if s.get("unique"):
            bits.append("UNIQUE")
        if s.get("references_table") and s.get("references_column"):
            rtab = s["references_table"]
            # 數字開頭 / 特殊字符表名 -> 加引號（5W2H）
            if rtab[0].isdigit() or not rtab.replace("_", "").isalnum():
                rtab = f'"{rtab}"'
            bits.append(f"REFERENCES {rtab}"
                        f"({s['references_column']})")
        if s.get("check_expr"):
            ce = s["check_expr"].replace("{col}", name)
            if ce.strip().upper().startswith("CHECK"):
                # formula 已含 CHECK (...) —— 唔再包（2026-10-25 value.formula）
                bits.append(ce)
            else:
                bits.append(f"CHECK ({ce})")
        if s.get("default_value") is not None:
            dv = s["default_value"]
            # 數字 -> 字串（0 / 1）
            if isinstance(dv, (int, float)):
                dv = str(dv)
            # 表達式 default（含括號/函數）要再包一層括號，否則 SQLite 語法錯
            elif "(" in dv and not dv.startswith("("):
                dv = f"({dv})"
            bits.append(f"DEFAULT {dv}")
        parts.append(" ".join(bits))
    return ", ".join(parts)