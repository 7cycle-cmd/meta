"""sql.py — mcp.db 存取層

mcp = Model Context Protocol 伺服器層
    mcp_server  伺服器字典（python / sql）
    mcp_tool    tool 字典（每個 server 有咩 tool）
    mcp_call    呼叫記錄（每次 tool 呼叫 = 一行，帶 source_id 證明）

設計原則（跟系統標準）：
    - 全部 by_id：server_id / tool_id / source_id 都係數字
    - 唔硬寫 id：server / tool 由 meta 查
    - 每次呼叫都要有 source_id（由 source module 證明來源）
    - 寫入經 guard（唯一入口）

用法：
    from mcp.sql import SqlStore
    s = SqlStore()
    s.add_server("python", "Python 執行環境 MCP")
    s.add_tool("python", "run_python", "執行 Python 代碼")
    s.record_call(server="python", tool="run_python",
                  source_id=11, ok=True, detail="...")
    s.close()
"""

import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\mcp_hub\mcp.db"

# ---------------- 字典表 ----------------


# ---------------- 呼叫記錄（證據） ----------------

# 預設 server（seed）：改呢度 = 改清單
DEFAULT_SERVERS = [
    ("python", "Python 執行環境 MCP（執行代碼 / 檢查語法 / import 檢查）",
     "stdio", "python -m mcp_hub.python_server"),
    ("sql", "SQL 查詢 MCP（查 DB / 列表 / 描述表 / EXPLAIN / schema dump）",
     "stdio", "python -m mcp_hub.sql_server"),
]

# 預設 tool（seed）：(server, tool, description)
DEFAULT_TOOLS = [
    ("python", "run_python", "執行 Python 代碼並回傳結果"),
    ("python", "check_syntax", "檢查 Python 語法（compile）"),
    ("python", "list_modules", "列出 workspace 可 import 嘅 module"),
    ("python", "import_check", "檢查一個 module 可唔可以 import"),
    ("sql", "list_dbs", "列出 workspace 所有 DB"),
    ("sql", "list_tables", "列出 DB 嘅表"),
    ("sql", "describe_table", "描述表結構（欄位 + 索引 + FK）"),
    ("sql", "query", "執行 SELECT 查詢（只讀）"),
    ("sql", "explain", "EXPLAIN 查詢計劃"),
    ("sql", "schema_dump", "匯出整個 DB 嘅 schema（DDL）"),
]


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            MCP_SERVER_DDL + MCP_TOOL_DDL + MCP_CALL_DDL)
        self.conn.commit()
        self._seed()

    def _seed(self):
        """預填 server + tool 字典（冪等）"""
        for meta, desc, transport, command in DEFAULT_SERVERS:
            self.conn.execute(
                "INSERT OR IGNORE INTO mcp_server"
                " (meta, description, transport, command) VALUES (?, ?, ?, ?)",
                (meta, desc, transport, command))
            self.conn.execute(
                "UPDATE mcp_server SET description = ?, transport = ?,"
                " command = ? WHERE meta = ?",
                (desc, transport, command, meta))
        for server, tool, desc in DEFAULT_TOOLS:
            sid = self._server_id(server)
            if sid is None:
                continue
            self.conn.execute(
                "INSERT OR IGNORE INTO mcp_tool"
                " (server_id, meta, description) VALUES (?, ?, ?)",
                (sid, tool, desc))
            self.conn.execute(
                "UPDATE mcp_tool SET description = ?"
                " WHERE server_id = ? AND meta = ?", (desc, sid, tool))
        self.conn.commit()

    # ---------------- server ----------------
    def _server_id(self, meta):
        r = self.conn.execute(
            "SELECT id FROM mcp_server WHERE meta = ?", (meta,)).fetchone()
        return r["id"] if r else None

    def servers(self, active_only=True):
        sql = "SELECT * FROM mcp_server"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def server(self, server_id):
        r = self.conn.execute(
            "SELECT * FROM mcp_server WHERE id = ?", (server_id,)).fetchone()
        return dict(r) if r else None

    def server_by_meta(self, meta):
        r = self.conn.execute(
            "SELECT * FROM mcp_server WHERE meta = ?", (meta,)).fetchone()
        return dict(r) if r else None

    def add_server(self, meta, description=None, transport="stdio",
                   command=None):
        """加一個 MCP server（冪等）"""
        self.conn.execute(
            "INSERT OR IGNORE INTO mcp_server"
            " (meta, description, transport, command) VALUES (?, ?, ?, ?)",
            (meta, description, transport, command))
        self.conn.commit()
        return self._server_id(meta)

    # ---------------- tool ----------------
    def _tool_id(self, server_id, meta):
        r = self.conn.execute(
            "SELECT id FROM mcp_tool WHERE server_id = ? AND meta = ?",
            (server_id, meta)).fetchone()
        return r["id"] if r else None

    def tools(self, server=None, active_only=True):
        sql = """SELECT t.*, s.meta AS server
                 FROM mcp_tool t JOIN mcp_server s ON s.id = t.server_id
                 WHERE 1=1"""
        args = []
        if active_only:
            sql += " AND t.is_active = 1"
        if server:
            sql += " AND s.meta = ?"
            args.append(server)
        sql += " ORDER BY t.server_id, t.id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def tool(self, tool_id):
        r = self.conn.execute(
            "SELECT * FROM mcp_tool WHERE id = ?", (tool_id,)).fetchone()
        return dict(r) if r else None

    def add_tool(self, server, meta, description=None, input_schema=None):
        """加一個 tool（冪等）

        server = server 名（python / sql）
        """
        sid = self._server_id(server)
        if sid is None:
            raise ValueError(f"server 唔存在: {server!r}（先 add_server）")
        self.conn.execute(
            "INSERT OR IGNORE INTO mcp_tool"
            " (server_id, meta, description, input_schema)"
            " VALUES (?, ?, ?, ?)", (sid, meta, description, input_schema))
        self.conn.commit()
        return self._tool_id(sid, meta)

    # ---------------- 呼叫記錄（證據） ----------------
    def record_call(self, server, tool, source_id, ok=True, task_id=None,
                    input_json=None, output_json=None, error=None,
                    duration_ms=None):
        """記錄一次 tool 呼叫（必須有 source_id 證明來源）

        server    = server 名（python / sql）
        tool      = tool 名（run_python / query ...）
        source_id = source.db source.id（證明來源，必填）
        ok        = 成功 / 失敗
        """
        if not source_id:
            raise ValueError(
                "source_id 必填：每次 MCP 呼叫都要有來源證明"
                "（source.db source.id）")
        sid = self._server_id(server)
        if sid is None:
            raise ValueError(f"server 唔存在: {server!r}")
        tid = self._tool_id(sid, tool)
        if tid is None:
            raise ValueError(f"tool 唔存在: {server}.{tool}")
        cur = self.conn.execute(
            "INSERT INTO mcp_call"
            " (server_id, tool_id, source_id, task_id, ok, input_json,"
            "  output_json, error, duration_ms)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (sid, tid, source_id, task_id, 1 if ok else 0, input_json,
             output_json, error, duration_ms))
        self.conn.commit()
        return cur.lastrowid

    def calls(self, server=None, tool=None, ok=None, limit=100):
        """列出呼叫記錄（可按 server / tool / ok 篩選）"""
        sql = """SELECT c.*, s.meta AS server, t.meta AS tool
                 FROM mcp_call c
                 JOIN mcp_server s ON s.id = c.server_id
                 JOIN mcp_tool t ON t.id = c.tool_id
                 WHERE c.is_active = 1"""
        args = []
        if server:
            sql += " AND s.meta = ?"
            args.append(server)
        if tool:
            sql += " AND t.meta = ?"
            args.append(tool)
        if ok is not None:
            sql += " AND c.ok = ?"
            args.append(1 if ok else 0)
        sql += " ORDER BY c.id DESC LIMIT ?"
        args.append(limit)
        return [dict(r) for r in self.conn.execute(sql, args)]

    def stats(self):
        """統計（證明唔係黑箱）"""
        return {
            "server": self.conn.execute(
                "SELECT COUNT(*) FROM mcp_server").fetchone()[0],
            "tool": self.conn.execute(
                "SELECT COUNT(*) FROM mcp_tool").fetchone()[0],
            "call": self.conn.execute(
                "SELECT COUNT(*) FROM mcp_call").fetchone()[0],
            "call_ok": self.conn.execute(
                "SELECT COUNT(*) FROM mcp_call WHERE ok = 1").fetchone()[0],
            "call_fail": self.conn.execute(
                "SELECT COUNT(*) FROM mcp_call WHERE ok = 0").fetchone()[0],
        }

    def tables(self):
        """列出全部表（證明唔係黑箱）"""
        return [r[0] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
            " AND name NOT LIKE 'sqlite_%' ORDER BY name")]

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()
