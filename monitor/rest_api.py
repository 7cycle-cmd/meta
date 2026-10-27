"""rest_api.py — monitor REST API

端點：
    GET /health                  健康檢查
    GET /current-structure       列出 structure 各實體類型當前行數
    GET /current-taxonomy        列出 taxonomy 各樹層當前行數
    POST /refresh                更新兩張快照表

啟動：
    python -m monitor.rest_api --port 9520
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .api import Monitor


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
        from guard import Guard
        m = Monitor()
        try:
            if path in ("/health", ""):
                self._send(200, {"status": "ok", "module": "monitor",
                                 "api": "monitor.rest_api"})
                return
            tok = self.headers.get("X-API-Token")
            if not tok:
                self._send(401, {"error": "需要 X-API-Token header"})
                return
            g = Guard()
            try:
                if not g.valid(tok):
                    self._send(401, {"error": f"token '{tok}' 無效"})
                    return
            finally:
                g.close()
            if path == "/current-structure":
                self._send(200, {"current_structure": m.list_current_structure()})
            elif path == "/current-taxonomy":
                self._send(200, {"current_taxonomy": m.list_current_taxonomy()})
            else:
                self._send(404, {"error": f"唔知 route: {path}"})
        except Exception as e:
            self._send(500, {"error": str(e)})
        finally:
            m.close()

    def do_POST(self):
        import urllib.parse
        path = self.path.split("?", 1)[0].rstrip("/")
        m = Monitor()
        try:
            tok = self.headers.get("X-API-Token")
            if not tok:
                self._send(401, {"error": "需要 X-API-Token header"})
                return
            from guard import Guard
            g = Guard()
            try:
                if not g.valid(tok):
                    self._send(401, {"error": f"token '{tok}' 無效"})
                    return
            finally:
                g.close()
            if path == "/refresh":
                res = m.refresh()
                self._send(200, {"status": "ok", "refresh": res})
            else:
                self._send(404, {"error": f"唔知 route: {path}"})
        except Exception as e:
            self._send(500, {"error": str(e)})
        finally:
            m.close()


def main(port=9520):
    print(f"monitor rest_api @ http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), _Handler).serve_forever()


if __name__ == "__main__":
    _port = 9520
    if "--port" in sys.argv:
        _port = int(sys.argv[sys.argv.index("--port") + 1])
    main(_port)
