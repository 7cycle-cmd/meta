# -*- coding: utf-8 -*-
"""worker/__init__.py — worker（LLM 代理）身份 package

worker = 執行任務嘅 LLM 代理（Laya / DeepSeek / Qwen ...）
    worker          代理字典（id | name | session_id | is_active）
    worker_ability  能力字典（generatic / desicion / can_text / can_visual）
    worker_identity 代理 × 能力對應（worker_id | ability_id）

用法：
    from worker import Worker
    w = Worker()
    w.list_workers()
    w.close()
"""

from .api import Worker

__all__ = ["Worker"]
__version__ = "1.0.0"
