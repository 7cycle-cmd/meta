"""api.py — worker.db 對外 API（代理字典 + 能力）"""

from .sql import SqlStore


class Worker:
    """worker（LLM 代理）身份層嘅對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def list_workers(self, active_only=True):
        """列出全部代理（LLM 名 + session_id）"""
        return self.store.workers(active_only)

    def get_worker(self, worker_id):
        """按 id 攞一個代理"""
        return self.store.get_worker(worker_id)

    def add_worker(self, name, session_id=None, provider_id=None):
        """新增一個代理（冪等）"""
        return self.store.add_worker(name, session_id, provider_id)

    def list_abilities(self, active_only=True):
        """列出能力字典（generatic / desicion / can_text / can_visual）"""
        return self.store.abilities(active_only)

    def list_identities(self, worker_id=None):
        """列出代理 × 能力對應（可按 worker 篩選）"""
        return self.store.identities(worker_id)

    def link_ability(self, worker_id, ability_id):
        """將一個能力 link 到一個代理（冪等）"""
        return self.store.link(worker_id, ability_id)

    def unlink_ability(self, worker_id, ability_id):
        """取消能力 link"""
        return self.store.unlink(worker_id, ability_id)

    # ---------- provider（執行環境/提供者字典） ----------
    def list_environments(self, active_only=True):
        """列出提供者字典（Local / cloud / openrouter / vscode）"""
        return self.store.environments(active_only)

    # ---------- worker_token（token 配額 + 用量 + 費用） ----------
    def list_tokens(self, worker_id=None, provider_id=None):
        """列出 token 配額（可按 worker / provider 篩選）"""
        return self.store.tokens(worker_id, provider_id)

    def add_token(self, worker_id, token=0, condition_id=None,
                  provider_id=1, input=0, output=0, fee=0.0):
        """新增一個 token 配額記錄（一個 worker × provider × condition 一行）"""
        return self.store.add_token(worker_id, token, condition_id,
                                    provider_id, input, output, fee)

    def update_token_usage(self, token_id, input=None, output=None, fee=None):
        """更新已用 token（累加）"""
        return self.store.update_token_usage(token_id, input, output, fee)

    # ---------- token_usage（每次執行嘅用量記錄，pay for use only） ----------
    def add_token_usage(self, task_id, llm_id, input=0, output=0, fee=0.0,
                        provider_id=None, cache_read=0, cache_write=0,
                        reasoning=0, model=None, latency_ms=None,
                        request_id=None):
        """記錄一次執行嘅 token 用量（Local 都記，fee=0）

        cache_read/cache_write = prompt cache token
        reasoning              = 思考 token
        model                  = 實際 model 名
        latency_ms             = 延遲
        request_id             = provider 嘅 request id（追帳單）
        """
        return self.store.add_token_usage(
            task_id, llm_id, input, output, fee, provider_id,
            cache_read, cache_write, reasoning, model, latency_ms, request_id)

    def list_token_usages(self, task_id=None, llm_id=None, provider_id=None,
                          limit=100):
        """列出用量記錄（可按 task / llm / provider 篩選）"""
        return self.store.token_usages(task_id, llm_id, provider_id, limit)

    def close(self):
        self.store.close()
