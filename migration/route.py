"""route.py — migration REST 路由（對外查询介面）

migration 本身唔係 API —— 呢個 route 只係俾人睇審計記錄：
    GET /migrations            列出全部 migration 記錄
    GET /migrations?module=xx  按 module 篩選
"""
