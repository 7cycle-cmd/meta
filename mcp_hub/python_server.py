"""python_server.py — Python MCP server（官方 SDK，stdio transport）

真正嘅 MCP server 進程，用 `mcp` 官方 SDK（FastMCP）。
唔係 DB 記錄殼 —— 呢個係 VSCode / Claude Desktop 可以直接連嘅 server。

啟動：
    python -m mcp_hub.python_server

VSCode 設定（.vscode/mcp.json）：
    {
      "servers": {
        "python": {
          "type": "stdio",
          "command": "python",
          "args": ["-m", "mcp_hub.python_server"],
          "cwd": "c:\\projects\\meta"
        }
      }
    }

Tools：
    run_python      執行 Python 代碼（subprocess，有 timeout）
    check_syntax    檢查 Python 語法（compile）
    list_modules    列出 workspace 可 import 嘅 module
    import_check    檢查一個 module 可唔可以 import
"""

import json
import os
import subprocess
import sys
import time

from mcp.server.fastmcp import FastMCP

META = r"C:\projects\meta"
sys.path.insert(0, META)

mcp = FastMCP("python")


def _source_id(name="codegen"):
    """由 source.db 查 source.id（唔硬寫數字）"""
    import sqlite3
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
    """記錄一次呼叫（帶 source 證明）—— 所有進度由 source module 證明"""
    try:
        from mcp_hub import Mcp
        m = Mcp()
        try:
            m.record_call("python", tool, _source_id(), ok=ok,
                          input_json=input_json, output_json=output_json,
                          error=error, duration_ms=duration_ms)
        finally:
            m.close()
    except Exception:  # noqa: BLE001
        pass  # 記錄失敗唔應該影響 tool 本身


@mcp.tool()
def run_python(code: str, timeout: int = 10) -> str:
    """執行 Python 代碼並回傳結果（stdout / stderr）

    Args:
        code: 要執行嘅 Python 代碼
        timeout: 超時秒數（預設 10）
    """
    start = time.perf_counter()
    ok, result, error = True, None, None
    try:
        # 注意：MCP server 用 stdio transport，子進程唔可以繼承 stdin/stdout
        # （否則會死鎖：子進程等 stdin，MCP client 等 server 回應）
        proc = subprocess.run(
            [sys.executable, "-c", code],
            stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace", cwd=META)
        if proc.returncode == 0:
            result = proc.stdout.strip()
        else:
            ok = False
            error = (proc.stderr or proc.stdout).strip()[:4000]
    except subprocess.TimeoutExpired:
        ok = False
        error = f"timeout（{timeout}s）"
    except Exception as e:  # noqa: BLE001
        ok = False
        error = str(e)
    duration = round((time.perf_counter() - start) * 1000, 2)
    _record("run_python", ok,
            json.dumps({"code": code}, ensure_ascii=False),
            json.dumps({"result": result}, ensure_ascii=False) if ok else None,
            error, duration)
    if ok:
        return result if result else "（冇輸出）"
    return f"ERROR: {error}"


@mcp.tool()
def check_syntax(code: str) -> str:
    """檢查 Python 語法（唔執行）

    Args:
        code: 要檢查嘅 Python 代碼
    """
    start = time.perf_counter()
    ok, error = True, None
    try:
        compile(code, "<mcp>", "exec")
    except SyntaxError as e:
        ok = False
        error = f"{e.msg}（line {e.lineno}, col {e.offset}）"
    duration = round((time.perf_counter() - start) * 1000, 2)
    _record("check_syntax", ok,
            json.dumps({"code": code}, ensure_ascii=False),
            None, error, duration)
    return "OK（語法正確）" if ok else f"ERROR: {error}"


@mcp.tool()
def list_modules() -> str:
    """列出 workspace 可 import 嘅 module（有 __init__.py 嘅資料夾）"""
    start = time.perf_counter()
    mods = []
    for root, dirs, files in os.walk(META):
        dirs[:] = [d for d in dirs
                   if d not in ("__pycache__", ".git", "node_modules")]
        if "__init__.py" in files and root != META:
            rel = os.path.relpath(root, META).replace("\\", ".")
            mods.append(rel)
    mods.sort()
    duration = round((time.perf_counter() - start) * 1000, 2)
    _record("list_modules", True, None,
            json.dumps({"count": len(mods)}, ensure_ascii=False),
            None, duration)
    return "\n".join(mods)


@mcp.tool()
def import_check(module: str) -> str:
    """檢查一個 module 可唔可以 import（真 import，唔係靜態分析）

    Args:
        module: module 名（例如 resource / codegen / mcp_hub）
    """
    start = time.perf_counter()
    code = f"import {module}; print('OK', {module}.__file__)"
    ok, result, error = True, None, None
    try:
        # stdin=DEVNULL：避免子進程等 stdin 造成死鎖
        proc = subprocess.run(
            [sys.executable, "-c", code],
            stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace", cwd=META)
        if proc.returncode == 0:
            result = proc.stdout.strip()
        else:
            ok = False
            error = (proc.stderr or proc.stdout).strip()[:2000]
    except Exception as e:  # noqa: BLE001
        ok = False
        error = str(e)
    duration = round((time.perf_counter() - start) * 1000, 2)
    _record("import_check", ok,
            json.dumps({"module": module}, ensure_ascii=False),
            json.dumps({"result": result}, ensure_ascii=False) if ok else None,
            error, duration)
    return result if ok else f"ERROR: {error}"


if __name__ == "__main__":
    mcp.run()
