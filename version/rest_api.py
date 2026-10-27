"""rest_api.py — version REST API 入口

標準 http.server（冇第三方依賴）；統一 pattern：
    127.0.0.1:PORT  -> 每個 module 一個 REST 接口

啟動：
    python -m version.rest_api --port 9500
"""

import json
import sys
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

    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/")
        if path in ("/health", ""):
            self._send(200, {"status": "ok",
                             "module": "version",
                             "api": "version.rest_api"})
        elif path == "/booleans":
            from .api import Version
            v = Version()
            try:
                self._send(200, {"booleans": v.booleans()})
            finally:
                v.close()
        elif path == "/versions":
            from .api import Version
            v = Version()
            try:
                self._send(200, {"versions": v.list()})
            finally:
                v.close()
        elif path == "/github-actions":
            from .api import Version
            v = Version()
            try:
                self._send(200, {"github_actions": v.github_actions()})
            finally:
                v.close()
        elif path == "/github-statuses":
            from .api import Version
            v = Version()
            try:
                self._send(200, {"github_statuses": v.github_statuses()})
            finally:
                v.close()
        elif path == "/githubs":
            from .api import Version
            v = Version()
            try:
                self._send(200, {"githubs": v.githubs()})
            finally:
                v.close()
        elif path == "/github-ignores":
            from .api import Version
            v = Version()
            try:
                self._send(200, {"github_ignores": v.github_ignores()})
            finally:
                v.close()
        else:
            self._send(404, {"error": f"唔知 route: {path}"})


def main(port=9500):
    print(f"version rest_api @ http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), _Handler).serve_forever()


if __name__ == "__main__":
    _port = 9500
    if "--port" in sys.argv:
        _port = int(sys.argv[sys.argv.index("--port") + 1])
    main(_port)
