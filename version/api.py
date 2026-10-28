"""version 對外介面 API

版本註冊表（registry：id | pass_id | value_id | github_id）
+ GitHub 操作記錄（commit / push）。
"""

from .sql import SqlStore


class Version:
    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    # ---------------- registry（版本註冊表）----------------
    def list(self):
        """列出註冊版本（registry JOIN value）"""
        return self.store.versions()

    def registries(self):
        """列出 registry 原始行（id | pass_id | value_id | github_id）"""
        return self.store.registries()

    def values(self):
        """列出版本值（value 表）"""
        return self.store.values()

    def add(self, version):
        """登記一個版本（返回 registry.id）"""
        return self.store.add_version(version)

    def set_github(self, registry_id, github_id):
        """連結 registry 行 -> github 操作記錄"""
        return self.store.set_registry_github(registry_id, github_id)

    def set_pass(self, registry_id, pass_id):
        """設定 registry 行嘅期望值（pass_id = expected.id）"""
        return self.store.set_registry_pass(registry_id, pass_id)

    # ---------------- boolean（yes / no 值表）----------------
    def booleans(self):
        """列出 yes/no 值表（0 = 否 / 1 = 是）"""
        return self.store.booleans()

    # ---------------- github_action / github_status（字典）----------------
    def github_actions(self):
        """列出 GitHub 動作（commit / push）"""
        return self.store.github_actions()

    def github_statuses(self):
        """列出 GitHub 狀態（pending / done / failed）"""
        return self.store.github_statuses()

    # ---------------- github（操作記錄）----------------
    def githubs(self):
        """列出 GitHub 操作記錄"""
        return self.store.githubs()

    def record_commit(self, github_session_id, version=None,
                      status="pending"):
        """記錄一次 commit"""
        return self.store.record_github(github_session_id, "commit",
                                        status=status, version=version)

    def record_push(self, github_session_id, version=None,
                    status="pending"):
        """記錄一次 push"""
        return self.store.record_github(github_session_id, "push",
                                        status=status, version=version)

    def set_status(self, github_id, status):
        """更新操作狀態（pending / done / failed）"""
        return self.store.set_github_status(github_id, status)

    # ---------------- github_ignore（忽略規則）----------------
    def github_ignores(self):
        """列出忽略規則（pattern + yes/no，值來自本 DB boolean）"""
        return self.store.github_ignores()

    def set_ignore(self, pattern, value, description=None):
        """設定忽略規則（value: 0 = 否 / 1 = 是）"""
        return self.store.set_github_ignore(pattern, value, description)

    def write_gitignore(self, path=None):
        """由 github_ignore 表生成 .gitignore"""
        if path:
            return self.store.write_gitignore(path)
        return self.store.write_gitignore()

    def close(self):
        self.store.close()