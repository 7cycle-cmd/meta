"""scan_all.py — structure 中央掃描器：全部 module 資源登記入 structure_resource

用戶要求（2026-10-28）：structure_resource 應該有全部資源，唔可以淨係 source。
呢個 scanner 一次過掃全部 module：
    schema   = 每個 module schema.py *_DDL（AST）
    function = 每個 module 全部公開 function/class（AST）
    api      = 每個 module 自己 db 嘅 api 表（有先讀）
    tool     = tool.db registry（一次過）

冪等：add_structure_resource 內部 WHERE NOT EXISTS。

用法：
    python -m structure.scan_all
"""

import importlib.util as _ilu
import os
import sqlite3
import sys

META = r"C:\projects\meta"

# stdlib ast（避開 cwd ast shadow）
_ast_sp = _ilu.spec_from_file_location(
    "_stdlib_ast", os.path.join(os.path.dirname(os.__file__), "ast.py"))
_ast = _ilu.module_from_spec(_ast_sp)
_ast_sp.loader.exec_module(_ast)


def _module_ids():
    """taxonomy registry：module_id <-> meta（tree 2 = module）"""
    c = sqlite3.connect(os.path.join(META, "taxonomy", "taxonomy.db"))
    c.row_factory = sqlite3.Row
    ids = {r["meta"]: r["id"] for r in c.execute(
        "SELECT id, meta FROM registry WHERE tree_id = 2 AND is_active = 1")}
    c.close()
    return ids


def _structure_ids():
    """structure.db：module_id -> (package_id, {file: file_id})"""
    c = sqlite3.connect(os.path.join(META, "structure", "structure.db"))
    c.row_factory = sqlite3.Row
    out = {}
    for r in c.execute(
            "SELECT sm.id, sm.module_id, sm.value, st.meta AS stype"
            " FROM structure_module sm"
            " JOIN structure_type st ON st.id = sm.structure_type_id"
            " WHERE sm.module_id IS NOT NULL"):
        out.setdefault(r["module_id"], {"package": None, "files": {}})
        if r["stype"] == "package":
            out[r["module_id"]]["package"] = r["id"]
        elif r["stype"] == "file":
            out[r["module_id"]]["files"][r["value"]] = r["id"]
    c.close()
    return out


def _scan_py(folder):
    """AST 掃一個 module：返回 {"schema": [(name, line)], "functions": [(file, name, line)]}"""
    schema = []
    functions = []
    # schema：只掃 schema.py
    sp = os.path.join(folder, "schema.py")
    if os.path.isfile(sp):
        try:
            with open(sp, "r", encoding="utf-8") as f:
                tree = _ast.parse(f.read(), filename=sp)
            for node in _ast.walk(tree):
                if isinstance(node, _ast.Assign):
                    for t in node.targets:
                        if isinstance(t, _ast.Name) and t.id.endswith("_DDL"):
                            schema.append((t.id, node.lineno))
        except (SyntaxError, OSError):
            pass
    # function/class：全部公開 .py
    seen = set()
    for fn in sorted(os.listdir(folder)):
        if not fn.endswith(".py") or fn.startswith("_"):
            continue
        path = os.path.join(folder, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                tree = _ast.parse(f.read(), filename=path)
        except (SyntaxError, OSError):
            continue
        for node in _ast.walk(tree):
            if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)):
                if node.name.startswith("_"):
                    continue
                if (fn, node.name) in seen:
                    continue
                seen.add((fn, node.name))
                functions.append((fn, node.name, node.lineno))
    return schema, functions


def _module_apis(module_name):
    """讀 module 自己 db 嘅 api 表（有先讀，冇 -> []）"""
    db = os.path.join(META, module_name, f"{module_name}.db")
    if not os.path.isfile(db):
        return []
    try:
        c = sqlite3.connect(db)
        c.row_factory = sqlite3.Row
        try:
            # 有冇 api 表
            has = c.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='api'"
            ).fetchone()
            if not has:
                return []
            rows = c.execute(
                "SELECT a.api, t.value AS method FROM api a"
                " LEFT JOIN api_type t ON t.id = a.api_type_id"
                " WHERE a.is_active = 1 ORDER BY a.api").fetchall()
            return [f"{r['method']} {r['api']}" for r in rows]
        finally:
            c.close()
    except Exception:
        return []


def scan_all():
    """掃全部 module 並登記（冪等），返回統計"""
    mods = _module_ids()
    sids = _structure_ids()
    from structure import Structure
    st = Structure()
    stats = {"modules": 0, "schema": 0, "function": 0, "api": 0}
    try:
        rid = {v: st.store.resource_type_id(v)
               for v in ("schema", "function", "api", "tool")}
        for meta, mid in sorted(mods.items()):
            folder = os.path.join(META, meta)
            if not os.path.isdir(folder):
                continue
            info = sids.get(mid)
            if not info or not info["package"]:
                continue
            pkg = info["package"]
            files = info["files"]
            schema, functions = _scan_py(folder)
            # schema
            sfile = files.get("schema.py")
            for name, line in schema:
                st.store.add_structure_resource(rid["schema"], name, pkg,
                                                line_number=line, file_id=sfile)
                stats["schema"] += 1
            # function
            for fn, name, line in functions:
                st.store.add_structure_resource(rid["function"], f"{fn}:{name}",
                                                pkg, line_number=line,
                                                file_id=files.get(fn))
                stats["function"] += 1
            # api（module 自己 db）
            for api_val in _module_apis(meta):
                st.store.add_structure_resource(rid["api"], api_val, pkg)
                stats["api"] += 1
            stats["modules"] += 1
        # tool：tool.db registry -> taxonomy 名
        try:
            tc = sqlite3.connect(os.path.join(META, "tool", "tool.db"))
            tc.row_factory = sqlite3.Row
            tx = sqlite3.connect(os.path.join(META, "taxonomy", "taxonomy.db"))
            tx.row_factory = sqlite3.Row
            try:
                for r in tc.execute(
                        "SELECT module_id FROM registry WHERE is_active = 1"):
                    nr = tx.execute(
                        "SELECT meta FROM registry WHERE id = ?",
                        (r["module_id"],)).fetchone()
                    name = nr["meta"] if nr else f"module_{r['module_id']}"
                    # tool 去邊個 package？module 自己
                    tmid = r["module_id"]
                    tinfo = sids.get(tmid)
                    t_pkg = tinfo["package"] if tinfo else None
                    if t_pkg:
                        st.store.add_structure_resource(rid["tool"], name, t_pkg)
            finally:
                tc.close()
                tx.close()
        except Exception:
            pass
    finally:
        st.close()
    return stats


def main():
    stats = scan_all()
    print(f"[structure.scan_all] modules={stats['modules']}"
          f" schema={stats['schema']} function={stats['function']}"
          f" api={stats['api']}")
    # 最終分佈
    c = sqlite3.connect(os.path.join(META, "structure", "structure.db"))
    c.row_factory = sqlite3.Row
    try:
        print("\n=== structure_resource 最終分佈 ===")
        for r in c.execute(
                "SELECT rt.value AS type, COUNT(*) AS n"
                " FROM structure_resource sr"
                " LEFT JOIN resource_type rt ON rt.id = sr.resource_type_id"
                " GROUP BY rt.value ORDER BY n DESC"):
            print(f"  {r['type'] or 'NULL':15s} {r['n']} 行")
        print("  TOTAL:", c.execute(
            "SELECT COUNT(*) FROM structure_resource").fetchone()[0])
    finally:
        c.close()


if __name__ == "__main__":
    sys.exit(main())
