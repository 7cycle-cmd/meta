"""route.py — structure.db CLI"""

import sys

from .api import Structure

USAGE = """用法：
    python -m structure.route [command]

commands:
    data-types               列出型別 × 性質字典（db_field_property）
    field-settings           列出欄位規格（structure_db_field）
    field-formats            列出原子格式 token（db_field_format）
    field-uniques            列出 unique 欄位名（db_field_unique）
    table-settings 列出通用欄位模板（db_table_setting）
    table-definitions        列出表定義（structure_db_table + structure_db_field）
    table-definition <db> <table>  列出單一表定義 + 生成 DDL
    structure-types          列出實體類型字典（structure_type）
    structure-addresses     列出實體地址字典（structure_address：type -> value）
    structure-taxonomies    列出樹層 ↔ 實體類型映射（structure_taxonomy）
    positions                列出位置字典（position）
    default-values           列出全部型別預設值（default_value）
    default-value-add --type SLUG --value untitled   登記型別預設值
    default-value-remove --type SLUG                 移除型別預設值
"""


def _type_id(s, name):
    """由型別名（SLUG / BOOLEAN...）反查 db_field_type.id"""
    rows = s.list_data_types()
    for r in rows:
        if r.get("type_name", "").upper() == name.upper():
            return r["id"]
    return None


def _arg(argv, name, default=None):
    """攞 --name 嘅值（例如 --type SLUG -> SLUG）"""
    if name in argv:
        i = argv.index(name) + 1
        if i < len(argv):
            return argv[i]
        return "" if default is None else default
    return default


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(USAGE)
        return 1
    return _main(argv)


def _main(argv):
    s = Structure()
    try:
        cmd = argv[0]
        if cmd == "data-types":
            for r in s.list_data_types():
                props = ", ".join(r.get("properties") or [])
                print(f"{r['id']}\t{r.get('type_name', '?')}"
                      f"\t{props}")
        elif cmd == "field-settings":
            for r in s.list_db_field_settings():
                props = ", ".join(r.get("properties") or [])
                print(f"{r['id']}\t{r.get('type_name') or ''}"
                      f"\t{props}")
        elif cmd == "field-formats":
            for r in s.list_db_field_formats():
                print(f"{r['id']}\t{r['format']}\tactive={r['is_active']}")
        elif cmd == "field-uniques":
            for r in s.list_db_field_uniques():
                print(f"{r['id']}\t{r['value']}")
        elif cmd == "field-xxxxs":
            for r in s.list_db_field_xxxxs():
                print(f"{r['id']}\t{r.get('unique_meta') or ''}"
                      f"\t{r.get('type_name') or ''}"
                      f"\t{r.get('setting_format') or ''}")
        elif cmd == "table-settings":
            for r in s.list_db_table_settings():
                print(f"{r['id']}\t{r['meta_key']}"
                      f"\ttype_id={r['db_field_type_id']}"
                      f"\tactive={r['is_active']}")
        elif cmd == "table-definitions":
            # 列出全部表定義 + 欄位
            defs = s.list_table_definitions()
            if not defs:
                print("（冇任何表定義）")
            for d in defs:
                cols = ", ".join(c["column_name"] for c in d["columns"])
                print(f"[{d['id']}] {d['db_file']}.{d['table_name']}"
                      f" — {d['description'] or ''}") 
                print(f"    columns: {cols}")
        elif cmd == "table-definition":
            # 單一表定義 + 生成 DDL
            if len(argv) < 3:
                print("用法：table-definition <db_file> <table_name>")
                return 1
            db_file, table = argv[1], argv[2]
            d = s.get_table_definition(db_file, table)
            if not d:
                print(f"（冇定義：{db_file}.{table}）")
            else:
                print(f"[{d['id']}] {d['db_file']}.{d['table_name']}"
                      f" — {d['description'] or ''}")
                for c in d["columns"]:
                    print(f"    {c.get('seq_id', c.get('position_id', '-'))}"
                          f"\t{c['column_name']}"
                          f"\t{c['type_name'] or ''}"
                          f"\tFTYPE={c['db_field_type_id'] or ''}")
            print()
            print("--- 生成 DDL ---")
            ddl = s.generate_table_ddl(db_file, table)
            print(ddl if ddl else "（冇定義又冇通用模板，生成唔到）")
        elif cmd == "structure-types":
            for r in s.list_structure_types():
                print(f"{r['id']}\t{r['meta']}\t{r['description'] or ''}")
        elif cmd == "structure-addresses":
            for r in s.list_structure_addresses():
                print(f"{r['id']}\t{r['structure_type']}\t{r['value']}")
        elif cmd == "structure-taxonomies":
            for r in s.list_structure_taxonomies():
                print(f"{r['id']}\t{r['tree']}\t{r['structure_type']}"
                      f"\t(tree={r['tree_id']}, stype={r['structure_type_id']})")
        elif cmd in ("positions", "seqs"):
            for r in s.list_positions():
                print(f"{r['id']}\t{r['meta']}\tactive={r['is_active']}")
        elif cmd == "default-values":
            for r in s.list_default_values():
                print(f"{r['id']}\t{r['type_name'] or r['db_field_type_id']}"
                      f"\t{r['value']}\tactive={r['is_active']}")
        elif cmd == "default-value-add":
            name = _arg(argv, "--type")
            value = _arg(argv, "--value")
            if not name or value is None:
                print("用法：default-value-add --type <型別名> --value <預設值>")
                return 1
            tid = _type_id(s, name)
            if not tid:
                print(f"型別唔存在: {name}（用 data-types 睇清單）")
                return 1
            did = s.add_default_value(tid, value)
            print(f"✅ {name}（type_id={tid}）default -> {value}（id={did}）")
        elif cmd == "default-value-remove":
            name = _arg(argv, "--type")
            if not name:
                print("用法：default-value-remove --type <型別名>")
                return 1
            tid = _type_id(s, name)
            if not tid:
                print(f"型別唔存在: {name}")
                return 1
            ok = s.remove_default_value(tid)
            print(f"{'✅ 已移除' if ok else '（原本就冇）'} {name} 嘅 default")
        else:
            print(USAGE)
            return 1
    finally:
        s.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())