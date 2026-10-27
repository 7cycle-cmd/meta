"""version module：bool 值表 + 版本字典 + GitHub 操作記錄（commit / push）。

用法：
    from version import Version
    v = Version()
    v.booleans()                   # yes/no 值表（0 = 否 / 1 = 是）
    v.list()                       # 版本清單
    v.github_actions()             # commit / push 字典
    v.github_ignores()             # .gitignore 規則（pattern + yes/no）
    v.record_commit("sess-xxx")    # 記錄一次 commit
    v.record_push("sess-xxx")      # 記錄一次 push
    v.set_status(github_id, "done")
    v.write_gitignore()            # 由表生成 .gitignore
    v.close()
"""

from .api import Version

__all__ = ["Version"]