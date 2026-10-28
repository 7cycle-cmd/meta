"""rest_api.py — permit REST API 入口

routes：
    GET  /health
    GET  /permits?subject=&permit_type=&object=
    GET  /subjects?subject_type=
    GET  /objects?object_type=
    GET  /can?subject=&subject_type=&permit_type=&object=&object_type=
    POST /permits   {"subject", "subject_type", "permit_type", "object", "object_type"}

啟動：
    python -m permit.rest_api --port 9600
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .api import Permit


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
        qs = {}
        if "?" in self.path:
            for p in self.path.split("?", 1)[1].split("&"):
                if "=" in p:
                    k, val = p.split("=", 1)
                    qs[k] = val
        return qs

    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/")
        p = Permit()
        try:
            if path in ("/health", ""):
                self._send(200, {"status": "ok", "module": "permit"})
            elif path == "/permits":
                qs = self._qs()
                self._send(200, {"permits": p.permits(
                    subject=qs.get("subject"),
                    permit_type=qs.get("permit_type"),
                    object=qs.get("object"))})
            elif path == "/subjects":
                qs = self._qs()
                self._send(200, {"subjects": p.subjects(
                    subject_type=qs.get("subject_type"))})
            elif path == "/objects":
                qs = self._qs()
                self._send(200, {"objects": p.objects(
                    object_type=qs.get("object_type"))})
            elif path == "/can":
                qs = self._qs()
                ok = p.can(qs.get("subject"), qs.get("subject_type"),
                           qs.get("permit_type"), qs.get("object"),
                           qs.get("object_type"))
                self._send(200, {"allowed": bool(ok)})
            else:
                self._send(404, {"error": f"唔知 route: {path}"})
        finally:
            p.close()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = {}
        if length:
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                body = {}
        path = self.path.split("?", 1)[0].rstrip("/")
        p = Permit()
        try:
            if path == "/permits":
                need = ["subject", "subject_type", "permit_type",
                        "object", "object_type"]
                if any(not body.get(k) for k in need):
                    self._send(400, {"error": "需要 subject + subject_type + permit_type + object + object_type"})
                else:
                    rid = p.add_permit(body["subject"], body["subject_type"],
                                       body["permit_type"], body["object"],
                                       body["object_type"])
                    self._send(200, {"permit_id": rid})
            else:
                self._send(404, {"error": f"唔知 route: {path}"})
        finally:
            p.close()


def main(port=9600):
    print(f"permit rest_api @ http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), _Handler).serve_forever()


if __name__ == "__main__":
    _port = 9600
    if "--port" in sys.argv:
        _port = int(sys.argv[sys.argv.index("--port") + 1])
    main(_port)