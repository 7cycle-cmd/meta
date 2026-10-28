"""rest_api.py — programming REST API 入口

標準 http.server（冇第三方依賴）；統一 pattern：
    127.0.0.1:PORT  -> 每個 module 一個 REST 接口

啟動：
    python -m programming.rest_api --port 9500
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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs


class _Handler(BaseHTTPRequestHandler):
    def _qs(self):
        q = self.path.split("?", 1)[1] if "?" in self.path else ""
        return {k: v[0] for k, v in parse_qs(q).items()}

    def _send(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass

    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/")
        if path in ("/health", ""):
            self._send(200, {"status": "ok",
                              "module": "programming",
                              "api": "programming.rest_api"})
        elif path == "/formula-types":
            # formula_type 字典（python×function / SQL×select ...）
            from programming import Programming
            p = Programming()
            try:
                lid = self._qs().get("language_id")
                self._send(200, {"formula_types": p.formula_types(
                    int(lid) if lid else None)})
            finally:
                p.close()
        elif path == "/file-line-types":
            # 檔案行範圍分段（?file_id= 可篩選）
            from programming import Programming
            p = Programming()
            try:
                fid = self._qs().get("file_id")
                self._send(200, {"rows": p.file_line_types(
                    int(fid) if fid else None)})
            finally:
                p.close()
        elif path == "/add-file-line-type":
            # 登記分段（?file_id=&start_line=&end_line=&language_id=&formula_type_id=&function_id=）
            q = self._qs()
            fid = q.get("file_id")
            if not fid:
                self._send(400, {"error": "需要 ?file_id="})
                return
            from programming import Programming
            p = Programming()
            try:
                rid = p.add_file_line_type(
                    int(q["file_id"]),
                    int(q.get("start_line", 1)),
                    int(q.get("end_line", 1)),
                    int(q.get("language_id", 1)),
                    int(q.get("formula_type_id", 1)),
                    int(q["function_id"]) if q.get("function_id") else None)
                self._send(200, {"file_line_type_id": rid,
                                 "rows": p.file_line_types(int(fid))})
            finally:
                p.close()
        elif path == "/line-lookup":
            # 俾一行行號搵 formula_type（?file_id=&line=）
            q = self._qs()
            fid = q.get("file_id")
            line = q.get("line")
            if not fid or not line:
                self._send(400, {"error": "需要 ?file_id=&line="})
                return
            from programming import Programming
            p = Programming()
            try:
                r = p.line_lookup(int(fid), int(line))
                self._send(200, {"match": dict(r) if r else None})
            finally:
                p.close()
        else:
            self._send(404, {"error": f"唔知 route: {path}"})


def main(port=9500):
    print(f"{module_name} rest_api @ http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), _Handler).serve_forever()


if __name__ == "__main__":
    _port = 9500
    if "--port" in sys.argv:
        _port = int(sys.argv[sys.argv.index("--port") + 1])
    main(_port)
