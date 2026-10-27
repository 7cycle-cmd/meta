"""api.py — source.db 對外 API

source = 來源字典（每個來源一行，其他表用 source_id 指過嚟）
例如：Anthropic spec、ISO/IEC 9075、Wikipedia: Identifier
provider = 提供者字典（例如 Anthropic、ISO/IEC、IETF）
industry / authority_level = 字典（2026-10-24p 歸 terminology，呢度唯讀代理）
"""

from .sql import SqlStore


class Source:
    """來源（source.db）嘅對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def list_sources(self):
        return self.store.sources()

    def get(self, source_id):
        r = self.store.source(source_id)
        return dict(r) if r else None

    def lookup(self, source):
        r = self.store.find_by_source(source)
        return dict(r) if r else None

    def register(self, source, description=None, provider_id=None):
        """註冊一個來源（先經 flow 驗證 + provider 證明）

        2026-10-24i（用戶要求）：唔可以就咁 INSERT ——
        要先行 flow（step 定義）+ 證明（provider 存在 + official_url），
        全部 pass 先准註冊。冇 provider 註冊 = 拒絕。

        source          = 來源名（例如 'Anthropic spec'）
        description     = 描述
        provider_id     = provider.id（證明）；冇 = 拒絕
        flow_name       = 驗證鏈（預設 'source'）
        返回 (id, created)；失敗 raise ValueError（原因）
        """
        if provider_id is None:
            raise ValueError(
                f"source '{source}' 冇 provider_id —— 一定要經"
                " flow 定義 + provider 證明先准註冊")
        # 1. provider 存在？
        prov = self.store.provider(provider_id) if provider_id else None
        if not prov:
            raise ValueError(f"provider_id={provider_id} 唔存在喺 provider 表")
        # 2. provider 有 official_url（證明）
        url = prov["official_url"] if "official_url" in prov.keys() else None
        if not url or not str(url).strip():
            raise ValueError(
                f"provider '{prov['meta']}' 冇 official_url ——"
                "冇 URL 證明，唔准註冊")
        # 3. 已存在 -> 返回（冪等）
        existing = self.store.find_by_source(source)
        if existing:
            return existing["id"], False
        # 4. 寫入（provider 證明已通過）
        sid = self.store.insert_source(source, description, provider_id)
        self.store.commit()
        return sid, True

    def update(self, source_id, **fields):
        self.store.update_source(source_id, **fields)
        self.store.commit()

    def deactivate(self, source_id):
        self.store.deactivate(source_id)
        self.store.commit()

    def count(self):
        return self.store.count()

    # ---------- authority_level ----------
    def list_authority_levels(self):
        return self.store.authority_levels()

    def get_authority_level(self, level_id):
        r = self.store.authority_level(level_id)
        return dict(r) if r else None

    def lookup_authority_level(self, meta):
        r = self.store.find_authority_level_by_meta(meta)
        return dict(r) if r else None

    def authority_level_by_value(self, level):
        r = self.store.find_authority_level_by_value(level)
        return dict(r) if r else None

    # ---------- provider ----------
    def list_providers(self):
        return self.store.providers()

    def get_provider(self, provider_id):
        r = self.store.provider(provider_id)
        return dict(r) if r else None

    def lookup_provider(self, meta):
        r = self.store.find_provider_by_meta(meta)
        return dict(r) if r else None

    def register_provider(self, meta, authority_level_id=None, industry_id=None, official_url=None, description=None):
        """註冊一個提供者（meta UNIQUE，重複會被 IGNORE）

        industry_id：行業（FK -> industry.id）
        如果傳入嘅 industry 名（dict {'meta': 'education'}）會自動建立。
        """
        existing = self.store.find_provider_by_meta(meta)
        if existing:
            return existing["id"], False
        pid = self.store.insert_provider(meta, authority_level_id, industry_id, official_url, description)
        self.store.commit()
        return pid, True

    def register_provider_by_industry(self, meta, industry_meta, authority_level_id=None, official_url=None, description=None):
        """註冊提供者 + 自動建立/搵 industry（terminology.db 管字典）"""
        ind = self.store.find_industry_by_meta(industry_meta)
        if not ind:
            iid, _ = self.register_industry(industry_meta)
        else:
            iid = ind["id"]
        return self.register_provider(meta, authority_level_id, iid, official_url, description)

    def update_provider(self, provider_id, **fields):
        self.store.update_provider(provider_id, **fields)
        self.store.commit()

    def deactivate_provider(self, provider_id):
        self.store.deactivate_provider(provider_id)
        self.store.commit()

    def count_providers(self):
        return self.store.count_providers()

    # ---------- industry ----------
    def list_industries(self):
        return self.store.industries()

    def get_industry(self, industry_id):
        r = self.store.industry(industry_id)
        return dict(r) if r else None

    def lookup_industry(self, meta):
        r = self.store.find_industry_by_meta(meta)
        return dict(r) if r else None

    def register_industry(self, meta, description=None):
        """註冊一個行業（terminology.db，industry 表已搬去嗰度）

        2026-10-24p：industry 屬字典 -> 由 terminology 管。
        寫入 terminology.db（冪等，meta UNIQUE）。
        """
        import sqlite3
        tc = sqlite3.connect(r"C:\projects\meta\terminology\terminology.db")
        try:
            existing = tc.execute(
                "SELECT id FROM industry WHERE meta = ?", (meta,)).fetchone()
            if existing:
                return existing[0], False
            cur = tc.execute(
                "INSERT OR IGNORE INTO industry (meta, description)"
                " VALUES (?, ?)", (meta, description))
            tc.commit()
            return cur.lastrowid, True
        finally:
            tc.close()

    # ---------- api 註冊（module 對外 API，表管理） ----------
    def apis(self):
        """列出本 module 對外開放嘅 API（含 type）"""
        return self.store.apis()

    # ---------- flow / step（同 question 一樣設計） ----------
    def flows(self, active_only=True):
        """列出全部 source flow"""
        return self.store.flows(active_only)

    def flow_steps(self, flow_name, active_only=True):
        """列出一個 flow 嘅全部 steps（JOIN source 證明）"""
        return self.store.flow_steps(flow_name, active_only)

    def add_flow(self, flow_name):
        """建立一條驗證鏈（冪等）"""
        return self.store.add_flow(flow_name)

    def add_step(self, flow_name, source_id, seq):
        """建立一個 step（冪等）
        source_id = source.id（檢查邊個來源）
        """
        return self.store.add_step(flow_name, source_id, seq)

    def run_flow(self, flow_name="source", save=True):
        """行一條 source 驗證鏈（run + result 記錄）"""
        return self.store.run_flow(flow_name, save)

    def runs(self, limit=20):
        """列出 run 記錄（含每步證明）"""
        return self.store.runs(limit)

    # ---------- source_proof（詞 → source 證明，source 資產） ----------
    def source_proof(self, word):
        """詞嘅 source 證明（source_proof 表）
        2026-10-24j（用戶要求）：proof source 由 source 擁有，
        question 經呢度查（唔再直接讀 terminology.db）。
        2026-10-24m：word_source 改名 source_proof。
        """
        return self.store.source_proof(word)

    def add_source_proof(self, word, source_id=None, proof=None,
                         description=None, registered_by=None, run_id=None):
        """登記詞 → source 證明（source_id 必須）

        2026-10-24l（用戶要求）：caller 記錄
        registered_by = 邊個 caller 批准註冊（verify / system...）
        run_id        = source flow run.id（批准嗰次驗證）
        """
        return self.store.add_source_proof(
            word, source_id=source_id, proof=proof, description=description,
            registered_by=registered_by, run_id=run_id)

    def try_register(self, word, source_id=None, proof=None,
                     caller="system", run_id=None):
        """caller 動作：試註冊詞 → source 證明

        2026-10-24l（用戶要求）：caller 話你知條件成立先註冊。
        檢查鏈（唔可以 fake）：
            1. source_id 有（冇 = 拒絕）
            2. source 存在
            3. provider 有 official_url（URL 證明）
        全部 pass -> 寫入 source_proof（記 caller + run_id）
        返回 {"registered": bool, "reason": str, "source_proof_id": n}
        """
        if source_id is None:
            return {"registered": False,
                    "reason": f"word '{word}' 冇 source_id —— 唔可以註冊",
                    "source_proof_id": None}
        prov = self.store.provider(source_id) if source_id else None
        if not prov:
            return {"registered": False,
                    "reason": f"source_id={source_id} 唔存在",
                    "source_proof_id": None}
        url = prov["official_url"] if "official_url" in prov.keys() else None
        if not url or not str(url).strip():
            return {"registered": False,
                    "reason": f"provider '{prov['meta']}' 冇 official_url",
                    "source_proof_id": None}
        # caller 條件通過 -> 註冊（記 caller + run_id）
        wsid = self.store.add_source_proof(
            word, source_id=source_id, proof=proof,
            registered_by=caller, run_id=run_id)
        return {"registered": True,
                "reason": f"caller '{caller}' 驗證通過 -> 已註冊",
                "source_proof_id": wsid}

    def close(self):
        self.store.close()