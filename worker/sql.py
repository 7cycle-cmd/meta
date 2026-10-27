"""sql.py — worker.db 存取層（代理字典 + 能力字典 + 對應）"""

import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\worker\worker.db"






# token_usage 表：每次執行嘅 token 用量（pay for use only，逐次記錄）
# task_id = task.db task.id（邊個 task）
# llm_id  = worker.id（邊個 LLM 代理）
# provider_id = provider.id（邊個 provider 收費）
# 完整量度（真實 LLM API 會回傳）：
#   input / output            = 用量 token
#   cache_read / cache_write  = prompt cache token（OpenAI/Anthropic 有）
#   reasoning                 = 思考 token（DeepSeek R1 / Qwen 有）
#   model                     = 實際 model 名（例如 deepseek/deepseek-chat）
#   latency_ms                = 延遲
#   request_id                = provider 嘅 request id（追查帳單）
#   fee                       = 費用

DEFAULT_WORKERS = [
    ("Laya", None, 1),                 # Local
    ("DeepSeek V4.1 Flash", None, 2),   # cloud
    ("DeepSeek V4 Flash 0731", None, 2),  # cloud
    ("Qwen 2.5-7b-instrct", None, 1),  # Local
    ("Qwen 2.5-7b-vl", None, 1),        # Local
]

# pay for use only：冇配額（配額概念已廢）
# Local / cloud / openrouter / vscode 全部按實際用量記錄（token_usage）

DEFAULT_ABILITIES = [
    ("generatic", "生成（代碼/檔案）"),
    ("desicion", "決策（揀邊條路）"),
    ("can_text", "可以處理文字"),
    ("can_visual", "可以處理視覺"),
]

DEFAULT_ENVIRONMENTS = [
    ("Local", "本地執行（本機 LLM）"),
    ("cloud", "雲端執行（API）"),
    ("openrouter", "OpenRouter API（第三方收費）"),
    ("vscode", "VS Code 內建（GitHub Copilot 收費）"),
]

# worker_identity（你寫嘅對應）：
#   1: Laya  -> desicion + can_text
#   2: DeepSeek V4.1 Flash -> generatic + can_text + can_visual
#   3: DeepSeek V4 Flash 0731 -> generatic + can_text + can_visual
#   4: Qwen 2.5-7b-instrct -> generatic + can_text + can_visual
#   5: Qwen 2.5-7b-vl -> (冇對應，照你原稿冇 avatar)
DEFAULT_IDENTITY = [
    (1, 2),   # Laya: desicion
    (1, 3),   # Laya: can_text
    (4, 1),   # Qwen instrct: generatic
    (4, 3),   # Qwen instrct: can_text
    (3, 1),   # 0731: generatic
    (3, 3),   # 0731: can_text
    (2, 1),   # 4.1: generatic
    (2, 3),   # 4.1: can_text
    (2, 4),   # 4.1: can_visual
    (4, 1),   # Qwen instrct: generatic（重複，IGNORE）
    (4, 3),   # Qwen instrct: can_text（重複，IGNORE）
    (4, 4),   # Qwen instrct: can_visual
]


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            WORKER_DDL + WORKER_ABILITY_DDL + WORKER_IDENTITY_DDL
            + PROVIDER_DDL + WORKER_TOKEN_DDL + TOKEN_USAGE_DDL)
        self.conn.commit()
        # 舊 token_usage 表補新欄位（保留資料）
        self._migrate_token_usage()
        self._seed()

    def _migrate_token_usage(self):
        """舊 token_usage（input/output/fee）補 cache_read / model / latency 等欄位"""
        cols = [c[1] for c in self.conn.execute("PRAGMA table_info('token_usage')")]
        for name, ddl in [
            ("cache_read", "INTEGER NOT NULL DEFAULT 0"),
            ("cache_write", "INTEGER NOT NULL DEFAULT 0"),
            ("reasoning", "INTEGER NOT NULL DEFAULT 0"),
            ("model", "TEXT"),
            ("latency_ms", "INTEGER"),
            ("request_id", "TEXT"),
        ]:
            if name not in cols:
                try:
                    self.conn.execute(f'ALTER TABLE token_usage ADD COLUMN "{name}" {ddl}')
                except Exception:
                    pass
        self.conn.commit()

    def _seed(self):
        """預填 worker / ability / identity / environment / token（冪等）"""
        for name, session, env_id in DEFAULT_WORKERS:
            self.conn.execute(
                "INSERT OR IGNORE INTO worker (name, session_id)"
                " VALUES (?, ?)", (name, session))
            # 更新 provider_id（唔蓋 session；有先填）
            self.conn.execute(
                "UPDATE worker SET provider_id = ?"
                " WHERE name = ? AND (provider_id IS NULL"
                "   OR provider_id != ?)",
                (env_id, name, env_id))
        # token 配額概念已廢（pay for use only）—— 唔再寫配額
        self.conn.commit()
        for ability, desc in DEFAULT_ABILITIES:
            self.conn.execute(
                "INSERT OR IGNORE INTO worker_ability (ability, description)"
                " VALUES (?, ?)", (ability, desc))
        # ability id 2=desicion, 3=can_text ...
        self.conn.execute(
            "INSERT OR IGNORE INTO worker_identity (worker_id, ability_id)"
            " VALUES (?, ?)", (1, 2))
        self.conn.execute(
            "INSERT OR IGNORE INTO worker_identity (worker_id, ability_id)"
            " VALUES (?, ?)", (1, 3))
        self.conn.execute(
            "INSERT OR IGNORE INTO worker_identity (worker_id, ability_id)"
            " VALUES (?, ?)", (4, 1))
        self.conn.execute(
            "INSERT OR IGNORE INTO worker_identity (worker_id, ability_id)"
            " VALUES (?, ?)", (4, 3))
        self.conn.execute(
            "INSERT OR IGNORE INTO worker_identity (worker_id, ability_id)"
            " VALUES (?, ?)", (3, 1))
        self.conn.execute(
            "INSERT OR IGNORE INTO worker_identity (worker_id, ability_id)"
            " VALUES (?, ?)", (3, 3))
        self.conn.execute(
            "INSERT OR IGNORE INTO worker_identity (worker_id, ability_id)"
            " VALUES (?, ?)", (2, 1))
        self.conn.execute(
            "INSERT OR IGNORE INTO worker_identity (worker_id, ability_id)"
            " VALUES (?, ?)", (2, 3))
        self.conn.execute(
            "INSERT OR IGNORE INTO worker_identity (worker_id, ability_id)"
            " VALUES (?, ?)", (2, 4))
        self.conn.execute(
            "INSERT OR IGNORE INTO worker_identity (worker_id, ability_id)"
            " VALUES (?, ?)", (4, 4))
        # provider seed（Local / cloud / openrouter / vscode）
        for meta, desc in DEFAULT_ENVIRONMENTS:
            self.conn.execute(
                "INSERT OR IGNORE INTO provider (meta, description)"
                " VALUES (?, ?)", (meta, desc))
        self.conn.commit()

    # ---------- worker ----------
    def workers(self, active_only=True):
        sql = """SELECT w.id, w.name, w.session_id, w.provider_id,
                         p.meta AS provider, w.is_active
                  FROM worker w
                  LEFT JOIN provider p ON p.id = w.provider_id
                  WHERE 1=1"""
        if active_only:
            sql += " AND w.is_active = 1"
        sql += " ORDER BY w.id"
        return [dict(r) for r in self.conn.execute(sql)]

    def get_worker(self, worker_id):
        sql = """SELECT w.*, p.meta AS provider
                  FROM worker w
                  LEFT JOIN provider p ON p.id = w.provider_id
                  WHERE w.id = ?"""
        r = self.conn.execute(sql, (worker_id,)).fetchone()
        return dict(r) if r else None

    def add_worker(self, name, session_id=None, provider_id=None):
        """新增/攞返 worker（冪等）"""
        self.conn.execute(
            "INSERT OR IGNORE INTO worker (name, session_id, provider_id)"
            " VALUES (?, ?, ?)",
            (name, session_id, provider_id))
        # 有 provider_id 就更新（唔蓋 session）
        if provider_id:
            self.conn.execute(
                "UPDATE worker SET provider_id = ? WHERE name = ?",
                (provider_id, name))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM worker WHERE name = ?", (name,)).fetchone()
        return r["id"] if r else None

    # ---------- ability ----------
    def abilities(self, active_only=True):
        sql = "SELECT * FROM worker_ability WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    # ---------- worker_identity（代理 × 能力） ----------
    def identities(self, worker_id=None, active_only=True):
        sql = """SELECT wi.id, wi.worker_id, w.name AS worker,
                        wi.ability_id, a.ability
                 FROM worker_identity wi
                 JOIN worker w ON w.id = wi.worker_id
                 JOIN worker_ability a ON a.id = wi.ability_id
                 WHERE 1=1"""
        args = ()
        if worker_id:
            sql += " AND wi.worker_id = ?"
            args = (worker_id,)
        if active_only:
            sql += " AND wi.is_active = 1"
        sql += " ORDER BY wi.id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def link(self, worker_id, ability_id):
        """將一個能力 link 到一個 worker（冪等）"""
        self.conn.execute(
            "INSERT OR IGNORE INTO worker_identity (worker_id, ability_id)"
            " VALUES (?, ?)", (worker_id, ability_id))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM worker_identity WHERE worker_id = ? AND ability_id = ?",
            (worker_id, ability_id)).fetchone()
        return r["id"] if r else None

    def unlink(self, worker_id, ability_id):
        """取消 link（soft delete）"""
        self.conn.execute(
            "UPDATE worker_identity SET is_active = 0"
            " WHERE worker_id = ? AND ability_id = ?",
            (worker_id, ability_id))
        self.conn.commit()

    # ---------- provider（執行環境/提供者字典） ----------
    def environments(self, active_only=True):
        """列出 provider 字典（Local / cloud / openrouter / vscode）"""
        sql = "SELECT * FROM provider WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    # ---------- worker_token（token 配額 + 用量 + 費用） ----------
    def tokens(self, worker_id=None, provider_id=None, active_only=True):
        """列出 token 配額（可按 worker / provider 篩選）"""
        sql = """SELECT t.id, t.worker_id, w.name AS worker,
                        t.provider_id, p.meta AS provider,
                        t.condition_id, t.token, t.input, t.output, t.fee
                 FROM worker_token t
                 JOIN worker w ON w.id = t.worker_id
                 LEFT JOIN provider p ON p.id = t.provider_id
                 WHERE 1=1"""
        args = ()
        if worker_id:
            sql += " AND t.worker_id = ?"
            args = (worker_id,)
        if provider_id:
            sql += " AND t.provider_id = ?"
            args = (provider_id,)
        if active_only:
            sql += " AND t.is_active = 1"
        sql += " ORDER BY t.id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def add_token(self, worker_id, token=0, condition_id=None,
                  provider_id=1, input=0, output=0, fee=0.0):
        """新增一個 token 配額記錄（一個 worker × provider × condition 一行）"""
        cur = self.conn.execute(
            "INSERT INTO worker_token"
            " (worker_id, provider_id, condition_id, token, input, output, fee)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (worker_id, provider_id, condition_id, token, input, output, fee))
        self.conn.commit()
        return cur.lastrowid

    def update_token_usage(self, token_id, input=None, output=None, fee=None):
        """更新已用 input / output / fee（累加）"""
        sets = []
        args = []
        if input is not None:
            sets.append("input = input + ?")
            args.append(input)
        if output is not None:
            sets.append("output = output + ?")
            args.append(output)
        if fee is not None:
            sets.append("fee = fee + ?")
            args.append(fee)
        if not sets:
            return 0
        sets.append("updated_at = datetime('now', 'localtime')")
        args.append(token_id)
        cur = self.conn.execute(
            "UPDATE worker_token SET " + ", ".join(sets) + " WHERE id = ?",
            args)
        self.conn.commit()
        return cur.rowcount

    # ---------- token_usage（每次執行嘅用量記錄，pay for use only） ----------
    def add_token_usage(self, task_id, llm_id, input=0, output=0, fee=0.0,
                        provider_id=None, cache_read=0, cache_write=0,
                        reasoning=0, model=None, latency_ms=None,
                        request_id=None):
        """記錄一次執行嘅 token 用量

        task_id     = task.db task.id（邊個 task）
        llm_id      = worker.id（邊個 LLM 代理）
        provider_id = provider.id；None = 自動由 worker 攞
        input/output/fee = 實際用量（Local 都記，fee=0）
        cache_read / cache_write / reasoning = prompt cache / 思考 token
        model       = 實際 model 名（例如 deepseek-chat）
        latency_ms  = 延遲
        request_id  = provider 嘅 request id（追帳單）
        """
        if provider_id is None:
            r = self.conn.execute(
                "SELECT provider_id FROM worker WHERE id = ?",
                (llm_id,)).fetchone()
            provider_id = r["provider_id"] if r else 1
        cur = self.conn.execute(
            "INSERT INTO token_usage"
            " (task_id, llm_id, provider_id, input, output, fee,"
            "  cache_read, cache_write, reasoning, model, latency_ms, request_id)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (task_id, llm_id, provider_id, input, output, fee,
             cache_read, cache_write, reasoning, model, latency_ms, request_id))
        self.conn.commit()
        return cur.lastrowid

    def token_usages(self, task_id=None, llm_id=None, provider_id=None,
                     limit=100):
        """列出用量記錄（可按 task / llm / provider 篩選）"""
        sql = """SELECT u.id, u.task_id, u.llm_id, w.name AS llm,
                        u.provider_id, p.meta AS provider,
                        u.input, u.output, u.fee,
                        u.cache_read, u.cache_write, u.reasoning,
                        u.model, u.latency_ms, u.request_id, u.created_at
                 FROM token_usage u
                 JOIN worker w ON w.id = u.llm_id
                 LEFT JOIN provider p ON p.id = u.provider_id
                 WHERE 1=1"""
        args = ()
        if task_id:
            sql += " AND u.task_id = ?"
            args = (task_id,)
        if llm_id:
            sql += " AND u.llm_id = ?"
            args = (llm_id,)
        if provider_id:
            sql += " AND u.provider_id = ?"
            args = (provider_id,)
        sql += " ORDER BY u.id DESC LIMIT ?"
        args += (limit,)
        return [dict(r) for r in self.conn.execute(sql, args)]

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()
