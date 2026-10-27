"""sweep — 清理 package

刪除殘留空表，每次動作自動寫入 proof.db（可追溯，唔會消失）。
cleanup 係 sweep module 嘅 skill（技能）。

模組分工：
    sql.py        清理記錄（proof.db cleanup 表）
    api.py        Sweep 類（run / history，dry_run 安全模式）
    route.py      CLI

用法：
    from sweep import Sweep
    c = Sweep()
    result = c.run(dry_run=True)   # 安全：先睇有咩可以清理
    result = c.run(dry_run=False)  # 真刪 + 寫 proof
    c.close()
"""

from .api import Sweep

__all__ = ["Sweep"]
__version__ = "1.0.0"