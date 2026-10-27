"""api.py — mcp.db 對外 API

mcp = Model Context Protocol 伺服器層
    python mcp  -> 執行 Python 代碼 / 檢查語法 / 列 module
    sql mcp     -> 查 DB / 列表 / 描述表 / EXPLAIN

每次呼叫都要有 source_id（由 source module 證明來源），
所以「所有進度都可以由 source module 證明」。

用法：
    from mcp_hub import Mcp
    m = Mcp()
    m.servers()                       # 列出 server（python / sql）
    m.tools("python")                 # 列出 python server 嘅 tool
    m.record_call("python", "run_python", source_id=11, ok=True,
                  input_json='{"code": "1+1"}', output_json='{"result": 2}')
    m.calls(server="python")          # 睇呼叫記錄
    m.close()
"""

import json

from .sql import SqlStore


class Mcp:
    """MCP 伺服器層（mcp.db）嘅對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    # ---------- server ----------
    def servers(self, active_only=True):
        """列出 MCP server（python / sql）"""
        return self.store.servers(active_only)

    def get_server(self, server_id):
        """按 server.id 攞 server"""
        return self.store.server(server_id)

    def lookup_server(self, meta):
        """按 server 名攞 server（只限內部用；跨 module 請用 id）"""
        return self.store.server_by_meta(meta)

    def add_server(self, meta, description=None, transport="stdio",
                   command=None):
        """加一個 MCP server（冪等）"""
        return self.store.add_server(meta, description, transport, command)

    # ---------- tool ----------
    def tools(self, server=None, active_only=True):
        """列出 tool（可按 server 篩選）"""
        return self.store.tools(server, active_only)

    def get_tool(self, tool_id):
        """按 tool.id 攞 tool"""
        return self.store.tool(tool_id)

    def add_tool(self, server, meta, description=None, input_schema=None):
        """加一個 tool（冪等）

        server = server 名（python / sql）
        """
        return self.store.add_tool(server, meta, description, input_schema)

    # ---------- 呼叫記錄（證據） ----------
    def record_call(self, server, tool, source_id, ok=True, task_id=None,
                    input_json=None, output_json=None, error=None,
                    duration_ms=None):
        """記錄一次 tool 呼叫（必須有 source_id 證明來源）

        server    = server 名（python / sql）
        tool      = tool 名（run_python / query ...）
        source_id = source.db source.id（證明來源，必填）
        ok        = 成功 / 失敗
        task_id   = task.db task.id（邊個 task 觸發，可選）
        """
        return self.store.record_call(
            server, tool, source_id, ok, task_id, input_json, output_json,
            error, duration_ms)

    def calls(self, server=None, tool=None, ok=None, limit=100):
        """列出呼叫記錄（可按 server / tool / ok 篩選）"""
        return self.store.calls(server, tool, ok, limit)

    # ---------- 實際執行（python / sql） ----------
    def run_python(self, code, source_id, task_id=None, timeout=10):
        """執行 Python 代碼（經 python mcp）

        code      = 要執行嘅 Python 代碼
        source_id = source.db source.id（證明來源，必填）
        返回 {"ok": bool, "result": ..., "error": str|None, "call_id": n}
        """
        import subprocess
        import sys
        import time
        start = time.perf_counter()
        ok, result, error = True, None, None
        try:
            proc = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True, text=True, timeout=timeout,
                encoding="utf-8", errors="replace")
            if proc.returncode == 0:
                result = proc.stdout.strip()
            else:
                ok = False
                error = (proc.stderr or proc.stdout).strip()[:2000]
        except subprocess.TimeoutExpired:
            ok = False
            error = f"timeout（{timeout}s）"
        except Exception as e:  # noqa: BLE001
            ok = False
            error = str(e)
        duration = round((time.perf_counter() - start) * 1000, 2)
        call_id = self.record_call(
            "python", "run_python", source_id, ok=ok, task_id=task_id,
            input_json=json.dumps({"code": code}, ensure_ascii=False),
            output_json=json.dumps({"result": result}, ensure_ascii=False)
            if ok else None,
            error=error, duration_ms=duration)
        return {"ok": ok, "result": result, "error": error,
                "call_id": call_id, "duration_ms": duration}

    def check_syntax(self, code, source_id, task_id=None):
        """檢查 Python 語法（經 python mcp）

        返回 {"ok": bool, "error": str|None, "call_id": n}
        """
        import time
        start = time.perf_counter()
        ok, error = True, None
        try:
            compile(code, "<mcp>", "exec")
        except SyntaxError as e:
            ok = False
            error = f"{e.msg}（line {e.lineno}）"
        duration = round((time.perf_counter() - start) * 1000, 2)
        call_id = self.record_call(
            "python", "check_syntax", source_id, ok=ok, task_id=task_id,
            input_json=json.dumps({"code": code}, ensure_ascii=False),
            error=error, duration_ms=duration)
        return {"ok": ok, "error": error, "call_id": call_id,
                "duration_ms": duration}

    def query(self, db_path, sql, source_id, task_id=None, limit=1000):
        """執行 SELECT 查詢（經 sql mcp，只讀）

        db_path   = DB 路徑
        sql       = SELECT 語句（只准 SELECT / WITH / PRAGMA）
        source_id = source.db source.id（證明來源，必填）
        返回 {"ok": bool, "rows": [...], "error": str|None, "call_id": n}
        """
        import sqlite3
        import time
        start = time.perf_counter()
        ok, rows, error = True, [], None
        head = sql.strip().split()[0].upper() if sql.strip() else ""
        if head not in ("SELECT", "WITH", "PRAGMA", "EXPLAIN"):
            ok = False
            error = f"只准 SELECT / WITH / PRAGMA / EXPLAIN，收到 {head}"
        else:
            try:
                c = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
                c.row_factory = sqlite3.Row
                try:
                    rows = [dict(r) for r in c.execute(sql).fetchmany(limit)]
                finally:
                    c.close()
            except sqlite3.Error as e:
                ok = False
                error = str(e)
        duration = round((time.perf_counter() - start) * 1000, 2)
        call_id = self.record_call(
            "sql", "query", source_id, ok=ok, task_id=task_id,
            input_json=json.dumps({"db": db_path, "sql": sql},
                                  ensure_ascii=False),
            output_json=json.dumps({"count": len(rows)}, ensure_ascii=False)
            if ok else None,
            error=error, duration_ms=duration)
        return {"ok": ok, "rows": rows, "error": error, "call_id": call_id,
                "duration_ms": duration}

    def list_tables(self, db_path, source_id, task_id=None):
        """列出 DB 嘅表（經 sql mcp）"""
        return self.query(
            db_path,
            "SELECT name FROM sqlite_master WHERE type='table'"
            " AND name NOT LIKE 'sqlite_%' ORDER BY name",
            source_id, task_id)

    def describe_table(self, db_path, table, source_id, task_id=None):
        """描述表結構（經 sql mcp）"""
        return self.query(db_path, f'PRAGMA table_info("{table}")',
                          source_id, task_id)

    # ---------- 統計 ----------
    def stats(self):
        """統計（證明唔係黑箱）"""
        return self.store.stats()

    def tables(self):
        """列出 mcp.db 全部表"""
        return self.store.tables()

    def close(self):
        self.store.close()
