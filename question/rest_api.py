"""api_server.py — question 嘅 REST API 伺服器（標準庫 http.server，零依賴）

用嚟測試 question flow：提交一個 value，系統自動判定 pass/fail，
寫入 run（證明）。

    GET  /health                  健康檢查
    GET  /run?value=build        提交一個值，行 5w2h flow，自動判定
         [?flow=5w2h]            （flow 名，預設 5w2h）
         [?answers={"1":true}]   （可選：手動 answers；冇就自動計）
    GET  /runs                   最近執行記錄（含 answers）
    GET  /questions              問題列表（operator + 期望值）
    GET  /values                 value 表
    GET  /expecteds              期望值字典
    GET  /operators              operator 字典
    GET  /tests                  test 維度

用法：
    python -m question.api_server [--port 8400]

例子：
    curl "http://127.0.0.1:8400/run?value=build"
    curl "http://127.0.0.1:8400/run?value=5W2H"
    curl "http://127.0.0.1:8400/runs"
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


import argparse
import json
import sqlite3
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

META = r"C:\projects\meta"

def _module_info():
    """question module 喺 resource.db registry 嘅資料（id + 名）

    動態查，唔硬寫 —— 返回 {"id": n, "name": str}（搵唔到 id=None）
    """
    try:
        conn = sqlite3.connect(r"C:\projects\meta\resource\resource.db")
        conn.row_factory = sqlite3.Row
        try:
            mod = conn.execute(
                "SELECT id, meta FROM registry WHERE meta = 'question'"
                " AND is_active = 1").fetchone()
            if not mod:
                return {"id": None, "name": "question"}
            return {"id": mod["id"], "name": mod["meta"]}
        finally:
            conn.close()
    except Exception:
        return {"id": None, "name": "question"}

def _skills():
    """攞 question module 嘅能力（= skill）

    能力唯一來源 = skill（taxonomy.registry tree=skill 真實技能名）。
    """
    try:
        import sqlite3 as _sq
        conn = _sq.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
        conn.row_factory = _sq.Row
        try:
            tid = conn.execute(
                "SELECT id FROM tree WHERE meta_key = 'skill'"
                " AND is_active = 1").fetchone()
            if not tid:
                return []
            return [dict(r) for r in conn.execute(
                "SELECT r.id, r.meta AS meta_key"
                " FROM registry r"
                " WHERE r.tree_id = ? AND r.is_active = 1"
                " ORDER BY r.meta", (tid["id"],))]
        finally:
            conn.close()
    except Exception:
        return []

def _run_flow(value, flow_name="5w2h", answers=None):
    """提交一個值，行 flow，自動判定（經 API）

    answers = None -> 由 _auto_answers(value) 自動計（唔可以 fake）
    返回：run_flow 結果 + module + flow（id + name，由 DB 查）
    """
    from question import Question
    q = Question()
    try:
        if answers is None:
            answers = q.store._auto_answers(value, flow_name)
        res = q.run_flow(flow_name, answers, value=value)
        # flow = {id, name}：由 flow 表查（唔 hardcode）
        flow_row = q.store.conn.execute(
            "SELECT id, flow_name FROM flow WHERE flow_name = ?"
            " AND is_active = 1", (flow_name,)).fetchone()
        res["flow"] = {
            "id": flow_row["id"] if flow_row else None,
            "name": flow_row["flow_name"] if flow_row else flow_name,
        }
        # module（id + 名，動態查唔硬寫）放最前
        res = {"module": _module_info(), **res}
        return res
    finally:
        q.close()

def _autodetect_answers(value, flow_name="5w2h"):
    """由值自動計 answers（同 run_terminology 一致）"""
    from question import Question
    q = Question()
    try:
        return q.store._auto_answers(value, flow_name)
    finally:
        q.close()

class ApiHandler(BaseHTTPRequestHandler):
    # ---------------- helpers ----------------
    def _send(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionAbortedError, ConnectionResetError,
                BrokenPipeError):
            # client 已斷線 -> 靜靜收工，唔好炸 traceback
            self.close_connection = True

    def log_message(self, *args):
        pass

    def _qs(self):
        """拆 query string -> dict（首個值）"""
        if "?" not in self.path:
            return {}
        q = urllib.parse.parse_qs(self.path.split("?", 1)[1])
        return {k: v[0] for k, v in q.items()}

    # ---------------- GET ----------------
    def _management_routes(self):
        """管理 route 由 db 查（唔 hardcode）

        2026-10-24h（用戶要求）：有 _id 表管理，code 都要升級。
        api 表（flow_id IS NULL）嘅 GET path = 管理 route；
        flow_id 非空 = flow 路由（由 shortcut 表分流）。
        """
        from question import Question as _Q
        _q = _Q()
        try:
            _q.store.conn.row_factory = __import__("sqlite3").Row
            rows = _q.store.conn.execute(
                "SELECT a.api FROM api a"
                " JOIN api_type t ON t.id = a.api_type_id"
                " WHERE a.is_active = 1 AND t.value = 'GET'"
                " AND a.flow_id IS NULL").fetchall()
            # `/sources/<id>` 呢種帶參數路徑 -> 只記前綴 `/sources`
            out = set()
            for r in rows:
                out.add(r["api"].split("<")[0].rstrip("/"))
            return out
        finally:
            _q.close()

    def _check_token(self, qs):
        """rest_api 守衛（2026-10-26：guard 只保留喺 HTTP 入口）

        token 由 ?token=xxx 提供，喺 common.db token 表驗證
        （token_id 存在 + is_active=1）。返回 token 或 None。
        """
        tok = qs.get("token")
        if not tok:
            return None
        conn = sqlite3.connect(r"C:\projects\meta\common\common.db")
        conn.row_factory = sqlite3.Row
        try:
            ok = conn.execute(
                "SELECT 1 FROM token WHERE token_id = ? AND is_active = 1",
                (tok,)).fetchone()
        except sqlite3.Error:
            ok = None
        finally:
            conn.close()
        return tok if ok else None


    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/")
        try:
            if path == "/health" or path == "":
                self._send(200, {"status": "ok",
                                 "module": "question",
                                 "api": "question.api_server"})
                return
            qs = self._qs()
            tok = self._check_token(qs)
            if not tok:
                self._send(401, {
                    "error": "需要有效 token（?token=xxx，common.db token 表）",
                    "code": 401,
                })
                return
            # 通用 flow 路由（2026-10-24）：唔 hardcode flow，
            # path 查 shortcut 表（/run -> 5w2h default、
            # /english -> english word、/spec -> industry spec...）
            # 管理 route = api 表（flow_id IS NULL）—— 唔再硬寫 tuple
            if path not in self._management_routes():
                qs = self._qs()
                value = qs.get("value")
                api_path = path
                # 支援 value 喺 path 入面：
                #   /english/567869578  （slash 後）
                #   /english=567869578  （等號後）
                if not value and "=" in path:
                    api_path, _, pv = path.partition("=")
                    value = pv or None
                if value:
                    value = urllib.parse.unquote(value)
                if not value:
                    # 最後一個 / 之後如果唔係已知 shortcut（e.g. /run/5w2h）
                    # 就當 value（e.g. /english/567869578）
                    parts = path.rsplit("/", 1)
                    if len(parts) == 2 and parts[1]:
                        cand = parts[1]
                        # 檢查前置 route 係咪 shortcut（flow 名）
                        from question import Question as _Q
                        _q = _Q()
                        try:
                            _f = _q.flow_by_shortcut(parts[0])
                        finally:
                            _q.close()
                        if _f:
                            api_path = parts[0]
                            value = cand
                if not value:
                    # 幫手 debug：話你知收咗咩、點解唔得、應該點寫
                    from question import Question as _Q
                    known_shortcuts = []
                    _q = _Q()
                    try:
                        known_shortcuts = [s["api_url"]
                                           for s in _q.shortcuts()]
                    finally:
                        _q.close()
                    self._send(400, {
                        "error": "要 value（提交值）",
                        "code": 400,
                        "received_path": path,
                        "why": "搵唔到 value —— 淨係得 route，冇提交值",
                        "patterns": [
                            "/<route>?value=<值>",
                            "/<route>=<值>",
                            "/<route>/<值>",
                        ],
                        "examples": [
                            "/english?value=567869578",
                            "/english=567869578",
                            "/english/567869578",
                        ],
                        "known_routes": known_shortcuts,
                    })
                    return
                from question import Question
                q = Question()
                try:
                    # flow = shortcut 表路由（api_url -> shortcut[flow_name]）
                    flow = q.flow_by_shortcut(api_path)
                    if not flow and qs.get("flow"):
                        flow = qs.get("flow")
                    if not flow:
                        # 2026-10-24k：唔再靜靜 fallback 做 default flow ——
                        # route 唔喺 shortcut 表 = 未知 API（400 講清楚）
                        known_shortcuts = [s["api_url"]
                                           for s in q.shortcuts()]
                        self._send(400, {
                            "error": "未知 route / 未有 flow",
                            "code": 400,
                            "received_path": api_path,
                            "why": "呢個 route 唔喺 shortcut 表，"
                                   "唔可以靜靜行 default flow",
                            "known_routes": known_shortcuts,
                            "patterns": [
                                "/<route>?value=<值>",
                                "/<route>=<值>",
                                "/<route>/<值>",
                            ],
                        })
                        return
                    res = _run_flow(value, flow,
                                    qs.get("answers") and
                                    json.loads(qs["answers"]))
                    self._send(200, res)
                finally:
                    q.close()
            elif path == "/shortcuts":
                from question import Question
                q = Question()
                try:
                    self._send(200, {"shortcuts": q.shortcuts()})
                finally:
                    q.close()
            elif path == "/flow":
                from question import Question
                q = Question()
                try:
                    self._send(200, {"flows": q.flows()})
                finally:
                    q.close()
            elif path == "/runs":
                from question import Question
                q = Question()
                try:
                    self._send(200, {"runs": q.flow_runs(limit=20)})
                finally:
                    q.close()
            elif path == "/questions":
                from question import Question
                q = Question()
                try:
                    self._send(200, {"questions": q.questions()})
                finally:
                    q.close()
            elif path == "/skills":
                self._send(200, {"skills": _skills()})
            elif path == "/modules":
                # 所有 module 嘅能力總覽（2026-10-27：能力 = skill）
                # 來源：taxonomy.db registry tree=module（真 module 清單）
                #       + tree=skill（真技能名）
                out = {}
                conn = sqlite3.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
                conn.row_factory = sqlite3.Row
                try:
                    mods = [dict(r) for r in conn.execute(
                        "SELECT r.id, r.meta, t.meta_key AS tree"
                        " FROM registry r JOIN tree t ON t.id = r.tree_id"
                        " WHERE r.is_active = 1 ORDER BY r.meta")]
                    sk = [dict(r) for r in conn.execute(
                        "SELECT r.id, r.meta FROM registry r"
                        " JOIN tree t ON t.id = r.tree_id"
                        " WHERE t.meta_key = 'skill' AND r.is_active = 1"
                        " ORDER BY r.meta")]
                finally:
                    conn.close()
                for m in mods:
                    if m["tree"] == "module":
                        out[m["meta"]] = [{"taxonomy_id": s["id"],
                                           "meta_key": s["meta"],
                                           "description": None}
                                          for s in sk]
                self._send(200, {"modules": out})
            elif path == "/expecteds":
                from question import Question
                q = Question()
                try:
                    self._send(200, {"expecteds": q.expecteds(),
                                     "operators": q.operators()})
                finally:
                    q.close()
            elif path == "/values":
                from question import Question
                q = Question()
                try:
                    self._send(200, {"values": q.values()})
                finally:
                    q.close()
            elif path == "/tests":
                from question import Question
                q = Question()
                try:
                    self._send(200, {"tests": q.tests()})
                finally:
                    q.close()
            elif path == "/dictionaries":
                # 字符集字典（character.db：symbol / letter / INT）
                # + owner 組合（programming.db：語言 × 格式 -> 允許符號/字母/數字/開頭）
                # —— 2026-10-24s：字符定義屬 character，語言規則屬 programming
                import sqlite3 as _sq
                _cc = _sq.connect(r"C:\projects\meta\character\character.db")
                _cc.row_factory = _sq.Row
                _pc = _sq.connect(r"C:\projects\meta\programming\programming.db")
                _pc.row_factory = _sq.Row
                try:
                    def _crows(t, where="1=1"):
                        return [dict(r) for r in _cc.execute(
                            f'SELECT * FROM "{t}" WHERE {where}'
                            " ORDER BY id")]
                    def _prows(t, where="1=1"):
                        return [dict(r) for r in _pc.execute(
                            f'SELECT * FROM "{t}" WHERE {where}'
                            " ORDER BY id")]
                    def _owner_syms(o_id):
                        """programming.owner_symbol JOIN character.symbol"""
                        ids = [r["symbol_id"] for r in _pc.execute(
                            "SELECT symbol_id FROM owner_symbol"
                            " WHERE owner_id = ? AND is_active = 1", (o_id,))]
                        vals = set()
                        for sid in ids:
                            r = _cc.execute(
                                "SELECT value FROM symbol WHERE id = ?",
                                (sid,)).fetchone()
                            if r:
                                vals.add(r["value"])
                        return sorted(vals)
                    def _owner_engs(o_id):
                        """programming.owner_letter JOIN character.letter"""
                        rows = _pc.execute(
                            "SELECT letter_id FROM owner_letter"
                            " WHERE owner_id = ? AND is_active = 1", (o_id,)).fetchall()
                        vals, fmts = set(), set()
                        for r in rows:
                            e = _cc.execute(
                                "SELECT e.value, ecf.value AS char_format"
                                " FROM letter e"
                                " LEFT JOIN letter_char_format ecf"
                                "  ON ecf.id = e.letter_char_format_id"
                                " WHERE e.id = ?", (r["letter_id"],)).fetchone()
                            if e:
                                vals.add(e["value"])
                                if e["char_format"]:
                                    fmts.add(e["char_format"])
                        return sorted(vals), sorted(fmts)
                    def _owner_ints(o_id):
                        """programming.owner_INT JOIN character.INT"""
                        ids = [r["int_id"] for r in _pc.execute(
                            "SELECT int_id FROM owner_INT"
                            " WHERE owner_id = ? AND is_active = 1", (o_id,))]
                        vals = set()
                        for iid in ids:
                            r = _cc.execute(
                                'SELECT value FROM "INT" WHERE id = ?',
                                (iid,)).fetchone()
                            if r:
                                vals.add(r["value"])
                        return sorted(vals)
                    def _owner_starts(o_id):
                        return [r["value"] for r in _pc.execute(
                            "SELECT value FROM start_char"
                            " WHERE owner_id = ? AND is_active = 1"
                            " ORDER BY value", (o_id,))]
                    # 字符集（character.db 基礎定義）
                    charset_out = {"symbol": _crows("symbol"),
                                   "letter": _crows("letter"),
                                   "INT": _crows("INT")}
                    # owner 組合（programming.db 規則 + character.db 值）
                    owner_out = {}
                    for o in _prows("owner"):
                        lang = _pc.execute(
                            "SELECT meta FROM programming_language"
                            " WHERE id = ?", (o["language_id"],)).fetchone()
                        fmt = _pc.execute(
                            "SELECT meta FROM data_format WHERE id = ?",
                            (o["format_id"],)).fetchone()
                        syms = _owner_syms(o["id"])
                        engs, eng_fmts = _owner_engs(o["id"])
                        ints = _owner_ints(o["id"])
                        starts = _owner_starts(o["id"])
                        owner_out[f"{lang['meta']}×{fmt['meta']}"] = {
                            "owner_id": o["id"],
                            "language": lang["meta"] if lang else None,
                            "format": fmt["meta"] if fmt else None,
                            "symbols": syms,
                            "letters": engs,
                            "letter_formats": eng_fmts,
                            "ints": ints,
                            "start_chars": starts,
                        }
                    self._send(200, {
                        "dictionaries": charset_out,
                        "owners": owner_out,
                    })
                finally:
                    _cc.close()
                    _pc.close()
            elif path == "/apis":
                # 本 module 對外 API 註冊（api 表，DB 管理）
                from question import Question
                q = Question()
                try:
                    self._send(200, {"apis": q.apis()})
                finally:
                    q.close()
            elif path == "/codes":
                # 本 module 檔案註冊（code_registry 表，DB 管理）
                from question import Question
                q = Question()
                try:
                    self._send(200, {"codes": q.code_registries(),
                                     "code_flows": q.code_flows(),
                                     "value_defnes": q.value_defnes(),
                                     "unique_defnes": q.unique_defnes()})
                finally:
                    q.close()
            else:
                self._send(404, {"error": f"唔知嘅 route: {path}"})
        except Exception as e:
            try:
                self._send(500, {"error": str(e)})
            except Exception:
                # _send 自己都炸（例如 client 斷線）-> 冇嘢可以做
                pass

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description="question REST API")
    parser.add_argument("--port", type=int, default=8400)
    args = parser.parse_args(argv)
    # ThreadingHTTPServer：並行處理 request（單線程會一個慢 request 阻住全部）
    server = ThreadingHTTPServer(("127.0.0.1", args.port), ApiHandler)
    server.daemon_threads = True
    print(f"✅ question API 伺服器起動: http://127.0.0.1:{args.port}")
    print(f"   測試: curl \"http://127.0.0.1:{args.port}/run?value=build\"")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
        server.server_close()

if __name__ == "__main__":
    main()