"""rest_api.py — resource REST API 入口

標準 http.server（冇第三方依賴）；統一 pattern：
    127.0.0.1:PORT  -> 每個 module 一個 REST 接口

啟動：
    python -m resource.rest_api --port 9500
"""
import sys

# ---- ast shadow 保衛（2026-10-27 fix）----
# C:\projects\meta\ast\ 資料夾 shadow 咗標準庫 ast -> traceback.print_exc()
# 內部 ast.parse() 崩潰 -> HTTP connection 被切斷（連 error JSON 都收唔到）。
# 喺其他地方 import traceback 之前，確保 sys.modules['ast'] = 標準庫 ast。
_ast_mod = sys.modules.get("ast")
if _ast_mod is None or (getattr(_ast_mod, "__file__", "") or "").startswith(r"C:\projects\meta"):
    _keep = [p for p in sys.path if p not in ("", r"C:\projects\meta")]
    _save = sys.path[:]
    try:
        sys.path = _keep
        import ast as _stdlib_ast
        sys.modules["ast"] = _stdlib_ast
    except Exception:
        pass
    finally:
        sys.path = _save


import json
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class _Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass

    def _qs(self):
        if "?" not in self.path:
            return {}
        q = urllib.parse.parse_qs(self.path.split("?", 1)[1])
        return {k: v[0] for k, v in q.items()}

    def _check_token(self, qs):
        """rest_api 守衛（2026-10-26：guard 只保留喺 HTTP 入口）

        token 由 ?token=xxx 或 X-API-Token header 提供，
        喺 common.db token 表驗證（存在 + is_active=1）。
        """
        tok = qs.get("token")
        if not tok:
            hdr = self.headers.get("X-API-Token")
            if hdr:
                tok = hdr
        if not tok:
            raise ValueError("需要 ?token=（guard.db registry 嘅有效 token）")
        from guard import Guard
        g = Guard()
        try:
            ok = g.valid(tok)
        finally:
            g.close()
        if not ok:
            raise ValueError(f"token '{tok}' 無效（guard.db registry 查無 / 已停用）")
        return tok

    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/")
        qs = self._qs()
        from resource import Resource
        r = Resource()
        try:
            if path in ("/health", ""):
                self._send(200, {"status": "ok",
                                  "module": "resource",
                                  "api": "resource.rest_api"})
                return
            # 2026-10-28（用戶設計）：resource_schema / resource_tool by_id
            if path == "/resource-schemas":
                t = qs.get("taxonomy_tree_id")
                s = qs.get("schema_registry_id")
                rows = r.list_resource_schemas(
                    int(t) if t else None,
                    int(s) if s else None)
                self._send(200, {"resource_schemas": rows})
            elif path == "/resource-tools":
                t = qs.get("taxonomy_tree_id")
                tl = qs.get("tool_registry_id")
                rows = r.list_resource_tools(
                    int(t) if t else None,
                    int(tl) if tl else None)
                self._send(200, {"resource_tools": rows})
            else:
                self._send(404, {"error": f"唔知 route: {path}"})
        finally:
            r.close()

    def do_POST(self):
        """POST：資源登記（by_id，冪等）

        POST /resource-schemas {taxonomy_tree_id, schema_registry_id}
        POST /resource-tools   {taxonomy_tree_id, tool_registry_id}
        """
        import urllib.parse
        path = self.path.split("?", 1)[0].rstrip("/")
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.headers and
                              self.rfile.read(length).decode("utf-8")
                              if length else "{}")
            from resource import Resource
            r = Resource()
            try:
                if path == "/resource-schemas":
                    t = body.get("taxonomy_tree_id")
                    s = body.get("schema_registry_id")
                    if t is None or s is None:
                        self._send(400, {"error": "需要 taxonomy_tree_id +"
                                                   " schema_registry_id"})
                        return
                    rid = r.add_resource_schema(t, s)
                    self._send(200, {"resource_schema_id": rid,
                                     "taxonomy_tree_id": t,
                                     "schema_registry_id": s})
                elif path == "/resource-tools":
                    t = body.get("taxonomy_tree_id")
                    tl = body.get("tool_registry_id")
                    if t is None or tl is None:
                        self._send(400, {"error": "需要 taxonomy_tree_id +"
                                                   " tool_registry_id"})
                        return
                    rid = r.add_resource_tool(t, tl)
                    self._send(200, {"resource_tool_id": rid,
                                     "taxonomy_tree_id": t,
                                     "tool_registry_id": tl})
                else:
                    self._send(404, {"error": f"唔知 route: {path}"})
            finally:
                r.close()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._send(500, {"error": str(e)})


def main(port=9500):
    print(f"resource rest_api @ http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), _Handler).serve_forever()


if __name__ == "__main__":
    _port = 9500
    if "--port" in sys.argv:
        _port = int(sys.argv[sys.argv.index("--port") + 1])
    main(_port)
