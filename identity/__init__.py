"""identity — 身份層 package

統一管理系統入面所有「名字 → id」嘅對應關係（表：registry）：
    package    -> package_id
    skill      -> skill_id
    flow       -> flow_id
    step       -> step_id

額外欄位：
    taxonomy_id  對應 taxonomy.db 嘅分類
    resource_id  對應 resource.db 嘅資源

模組分工：
    sql.py       identity.db 存取層（registry 表）
    api.py       對外 API（Identity 類）
    route.py     命令行入口（CLI）

用法：
    from identity import Identity
    i = Identity()
    i.lookup("package", "codegen")      # -> {"id": 1, "name": "codegen"}
    i.lookup("flow", "create_table")    # -> {"id": 1, "name": "create_table"}
    i.close()
"""

from .api import Identity

__all__ = ["Identity"]
__version__ = "1.1.0"
