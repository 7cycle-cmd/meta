"""mcp_hub — MCP 伺服器層 package（真正嘅 MCP server + 呼叫記錄）

2026-10-22 改名：原本叫 `mcp`，但會 **shadow 官方 `mcp` SDK**
（`import mcp` 會拿到我哋嘅資料夾，`from mcp.server.fastmcp import FastMCP`
 拋 ModuleNotFoundError）。所以改名 `mcp_hub`。

兩個真正嘅 MCP server（官方 SDK，stdio transport）：
    python_server.py  -> python mcp（run_python / check_syntax /
                         list_modules / import_check）
    sql_server.py     -> sql mcp（list_dbs / list_tables / describe_table /
                         query / explain / schema_dump）

所有進度由 source module 證明：
    每次 tool 呼叫都寫入 mcp_call，帶 source_id（source.db source.id）。

模組分工：
    sql.py           資料庫存取層（mcp_server / mcp_tool / mcp_call）
    api.py           對外 API（Mcp 類）
    python_server.py 真正嘅 Python MCP server（FastMCP）
    sql_server.py    真正嘅 SQL MCP server（FastMCP）
    route.py         命令行入口（CLI）

用法：
    # 1. 啟動 MCP server（VSCode 會自動做）
    python -m mcp_hub.python_server
    python -m mcp_hub.sql_server

    # 2. 直接呼叫（唔經 MCP protocol）
    from mcp_hub import Mcp
    m = Mcp()
    m.servers()                       # python / sql
    m.tools("python")                 # python server 嘅 tool
    m.run_python("1+1", source_id=11) # 執行 + 記錄證據
    m.calls(server="python")          # 睇呼叫記錄
    m.close()
"""

from .api import Mcp

__all__ = ["Mcp"]
__version__ = "2.0.0"
