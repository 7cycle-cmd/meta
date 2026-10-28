
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

"""rest_api.py — lineage REST API"""

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .api import Lineage


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

    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/")
        qs = {}
        if "?" in self.path:
            for p in self.path.split("?", 1)[1].split("&"):
                if "=" in p:
                    k, val = p.split("=", 1)
                    qs[k] = val
        lg = Lineage()
        try:
            if path in ("/health", ""):
                self._send(200, {"status": "ok", "module": "lineage"})
            elif path == "/lineage":
                vid = int(qs["value_id"]) if qs.get("value_id") else None
                rid = int(qs["run_id"]) if qs.get("run_id") else None
                fid = int(qs["flow_id"]) if qs.get("flow_id") else None
                tid = int(qs["taxonomy_id"]) if qs.get("taxonomy_id") else None
                self._send(200, {"lineage": lg.list(
                    value_id=vid, run_id=rid, flow_id=fid, taxonomy_id=tid)})
            else:
                self._send(404, {"error": f"唔知 route: {path}"})
        finally:
            lg.close()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = {}
        if length:
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                body = {}
        path = self.path.split("?", 1)[0].rstrip("/")
        lg = Lineage()
        try:
            if path == "/lineage":
                vid = body.get("value_id")
                if not vid:
                    self._send(400, {"error": "需要 value_id"})
                else:
                    lgid = lg.add(vid, body.get("run_id"),
                                  body.get("flow_id"), body.get("step_id"),
                                  body.get("resource_id"),
                                  body.get("taxonomy_id"),
                                  body.get("value"))
                    self._send(200, {"lineage_id": lgid})
            else:
                self._send(404, {"error": f"唔知 route: {path}"})
        finally:
            lg.close()


def main(port=9900):
    print(f"lineage rest_api @ http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), _Handler).serve_forever()


if __name__ == "__main__":
    _port = 9900
    if "--port" in sys.argv:
        _port = int(sys.argv[sys.argv.index("--port") + 1])
    main(_port)