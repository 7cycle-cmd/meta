"""sql_server.py — SQL MCP server（官方 SDK，stdio transport）

真正嘅 MCP server 進程，用 `mcp` 官方 SDK（FastMCP）。
只讀（mode=ro），唔會改任何 DB。

啟動：
    python -m mcp_hub.sql_server

VSCode 設定（.vscode/mcp.json）：
    {
      "servers": {
        "sql": {
          "type": "stdio",
          "command": "python",
          "args": ["-m", "mcp_hub.sql_server"],
          "cwd": "c:\\projects\\meta"
        }
      }
    }

Tools：
    list_dbs        列出 workspace 所有 DB
    list_tables     列出一個 DB 嘅表
    describe_table  描述表結構（欄位 + 型別 + 約束）
    query           執行 SELECT（只讀，有 LIMIT）
    explain         EXPLAIN 查詢計劃
    schema_dump     匯出整個 DB 嘅 schema（DDL）
"""

import json
import os
import sqlite3
import sys
import time

from mcp.server.fastmcp import FastMCP

META = r"C:\projects\meta"
sys.path.insert(0, META)

mcp = FastMCP("sql")

# 只准呢啲語句（只讀）
_ALLOWED = ("SELECT", "WITH", "PRAGMA", "EXPLAIN")


def _source_id(name="codegen"):
    """由 source.db 查 source.id（唔硬寫數字）"""
    p = os.path.join(META, "source.db")
    if not os.path.isfile(p):
        return None
    c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    try:
        r = c.execute(
            "SELECT id FROM source WHERE source = ? AND is_active = 1",
            (name,)).fetchone()
        return r[0] if r else None
    except sqlite3.Error:
        return None
    finally:
        c.close()


def _record(tool, ok, input_json=None, output_json=None, error=None,
            duration_ms=None):
    """記錄一次呼叫（帶 source 證明）"""
    try:
        from mcp_hub import Mcp
        m = Mcp()
        try:
            m.record_call("sql", tool, _source_id(), ok=ok,
                          input_json=input_json, output_json=output_json,
                          error=error, duration_ms=duration_ms)
        finally:
            m.close()
    except Exception:  # noqa: BLE001
        pass


def _resolve_db(db: str) -> str:
    """把 db 名解析成完整路徑（唔准跳出 META）"""
    if os.path.isabs(db):
        path = db
    else:
        path = os.path.join(META, db)
    real = os.path.realpath(path)
    if not real.startswith(os.path.realpath(META)):
        raise ValueError(f"DB 路徑唔准跳出 workspace: {db}")
    if not os.path.isfile(real):
        raise ValueError(f"DB 唔存在: {db}")
    return real


def _ro(db: str):
    """開只讀連線"""
    return sqlite3.connect(f"file:{_resolve_db(db)}?mode=ro", uri=True)


@mcp.tool()
def list_dbs() -> str:
    """列出 workspace 所有 SQLite DB（檔名 + 表數 + 行數）"""
    start = time.perf_counter()
    out = []
    for name in sorted(os.listdir(META)):
        if not name.endswith(".db") or ".bak" in name:
            continue
        try:
            c = _ro(name)
            try:
                tables = [r[0] for r in c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                    " AND name NOT LIKE 'sqlite_%'")]
                rows = 0
                for t in tables:
                    try:
                        rows += c.execute(
                            f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                    except sqlite3.Error:
                        pass
                out.append(f"{name:<24} {len(tables):>3} 表 {rows:>8} 行")
            finally:
                c.close()
        except sqlite3.Error as e:
            out.append(f"{name:<24} ERR {e}")
    duration = round((time.perf_counter() - start) * 1000, 2)
    _record("list_dbs", True, None,
            json.dumps({"count": len(out)}, ensure_ascii=False),
            None, duration)
    return "\n".join(out)


@mcp.tool()
def list_tables(db: str) -> str:
    """列出一個 DB 嘅所有表（表名 + 行數）

    Args:
        db: DB 檔名（例如 resource.db）
    """
    start = time.perf_counter()
    ok, out, error = True, [], None
    try:
        c = _ro(db)
        try:
            for (t,) in c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                    " AND name NOT LIKE 'sqlite_%' ORDER BY name"):
                try:
                    n = c.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                except sqlite3.Error:
                    n = -1
                out.append(f"{t:<28} {n:>8} 行")
        finally:
            c.close()
    except (sqlite3.Error, ValueError) as e:
        ok, error = False, str(e)
    duration = round((time.perf_counter() - start) * 1000, 2)
    _record("list_tables", ok,
            json.dumps({"db": db}, ensure_ascii=False),
            json.dumps({"count": len(out)}, ensure_ascii=False) if ok else None,
            error, duration)
    return "\n".join(out) if ok else f"ERROR: {error}"


@mcp.tool()
def describe_table(db: str, table: str) -> str:
    """描述表結構（欄位 / 型別 / NOT NULL / 預設值 / PK）

    Args:
        db: DB 檔名（例如 resource.db）
        table: 表名（例如 registry）
    """
    start = time.perf_counter()
    ok, out, error = True, [], None
    try:
        c = _ro(db)
        try:
            cols = list(c.execute(f'PRAGMA table_info("{table}")'))
            if not cols:
                raise ValueError(f"表唔存在: {table}")
            out.append(f"{'欄位':<24} {'型別':<10} {'NOT NULL':<9}"
                       f" {'預設':<20} PK")
            for r in cols:
                out.append(f"{r[1]:<24} {r[2]:<10} {('YES' if r[3] else ''):<9}"
                           f" {str(r[4] or ''):<20} {'PK' if r[5] else ''}")
            # 索引
            idx = list(c.execute(f'PRAGMA index_list("{table}")'))
            if idx:
                out.append("\n索引:")
                for i in idx:
                    cols_i = [x[2] for x in c.execute(
                        f'PRAGMA index_info("{i[1]}")')]
                    out.append(f"  {i[1]:<40} unique={i[2]}"
                               f" ({', '.join(cols_i)})")
            # FK
            fks = list(c.execute(f'PRAGMA foreign_key_list("{table}")'))
            if fks:
                out.append("\nFK:")
                for f in fks:
                    out.append(f"  {f[3]} -> {f[2]}.{f[4]}")
        finally:
            c.close()
    except (sqlite3.Error, ValueError) as e:
        ok, error = False, str(e)
    duration = round((time.perf_counter() - start) * 1000, 2)
    _record("describe_table", ok,
            json.dumps({"db": db, "table": table}, ensure_ascii=False),
            None, error, duration)
    return "\n".join(out) if ok else f"ERROR: {error}"


@mcp.tool()
def query(db: str, sql: str, limit: int = 100) -> str:
    """執行 SELECT 查詢（只讀，自動加 LIMIT）

    Args:
        db: DB 檔名（例如 resource.db）
        sql: SELECT / WITH / PRAGMA / EXPLAIN 語句
        limit: 最多回傳幾多行（預設 100）
    """
    start = time.perf_counter()
    ok, out, error = True, [], None
    head = sql.strip().split()[0].upper() if sql.strip() else ""
    if head not in _ALLOWED:
        ok = False
        error = f"只准 {_ALLOWED}，收到 {head}"
    else:
        try:
            c = _ro(db)
            c.row_factory = sqlite3.Row
            try:
                rows = c.execute(sql).fetchmany(limit)
                if not rows:
                    out.append("（0 行）")
                else:
                    keys = rows[0].keys()
                    out.append(" | ".join(keys))
                    out.append("-" * 60)
                    for r in rows:
                        out.append(" | ".join(
                            "" if r[k] is None else str(r[k])[:60]
                            for k in keys))
                    out.append(f"\n（{len(rows)} 行，limit={limit}）")
            finally:
                c.close()
        except (sqlite3.Error, ValueError) as e:
            ok, error = False, str(e)
    duration = round((time.perf_counter() - start) * 1000, 2)
    _record("query", ok,
            json.dumps({"db": db, "sql": sql}, ensure_ascii=False),
            json.dumps({"lines": len(out)}, ensure_ascii=False) if ok else None,
            error, duration)
    return "\n".join(out) if ok else f"ERROR: {error}"


@mcp.tool()
def explain(db: str, sql: str) -> str:
    """EXPLAIN 查詢計劃（唔執行查詢）

    Args:
        db: DB 檔名
        sql: 要分析嘅 SQL
    """
    start = time.perf_counter()
    ok, out, error = True, [], None
    try:
        c = _ro(db)
        c.row_factory = sqlite3.Row
        try:
            for r in c.execute(f"EXPLAIN QUERY PLAN {sql}"):
                out.append(f"  {r['detail']}")
        finally:
            c.close()
    except (sqlite3.Error, ValueError) as e:
        ok, error = False, str(e)
    duration = round((time.perf_counter() - start) * 1000, 2)
    _record("explain", ok,
            json.dumps({"db": db, "sql": sql}, ensure_ascii=False),
            None, error, duration)
    return "\n".join(out) if ok else f"ERROR: {error}"


@mcp.tool()
def schema_dump(db: str) -> str:
    """匯出整個 DB 嘅 schema（所有 CREATE 語句）

    Args:
        db: DB 檔名
    """
    start = time.perf_counter()
    ok, out, error = True, [], None
    try:
        c = _ro(db)
        try:
            for r in c.execute(
                    "SELECT type, name, sql FROM sqlite_master"
                    " WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'"
                    " ORDER BY type, name"):
                out.append(f"-- [{r[0]}] {r[1]}")
                out.append(r[2] + ";")
                out.append("")
        finally:
            c.close()
    except (sqlite3.Error, ValueError) as e:
        ok, error = False, str(e)
    duration = round((time.perf_counter() - start) * 1000, 2)
    _record("schema_dump", ok,
            json.dumps({"db": db}, ensure_ascii=False),
            json.dumps({"lines": len(out)}, ensure_ascii=False) if ok else None,
            error, duration)
    return "\n".join(out) if ok else f"ERROR: {error}"


if __name__ == "__main__":
    mcp.run()
