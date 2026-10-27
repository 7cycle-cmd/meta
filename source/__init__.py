"""source — 來源 package

source = 來源字典（每個來源一行，其他表用 source_id 指過嚟）
例如：Anthropic spec、ISO/IEC 9075、Wikipedia: Identifier
provider = 提供者字典（例如 Anthropic、ISO/IEC、IETF）
authority_level = 權威等級（官方 2 / 權威參考 1 / 非官方 0）
industry = 行業字典（例如 information technology）

模組分工：
    sql.py        資料庫存取層（source + provider + authority_level + industry 表）
    api.py        對外 API（Source 類）
    api_server.py REST API 伺服器（JSON POST / GET）
    route.py      命令行入口（CLI）

用法：
    from source import Source
    s = Source()
    s.register_provider("Anthropic", authority_level_id=2)
    s.register("Anthropic spec", "模型上下文化協定", provider_id=1)
    s.lookup("Anthropic spec")
    s.close()
"""

from .api import Source

__all__ = ["Source"]
__version__ = "1.2.0"