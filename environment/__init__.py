"""environment/__init__.py — environment（執行環境）package

environment = 執行環境（computer / IDE / Browser / APP）
    type                  環境類型字典（computer / IDE / Browser / APP）
    environment_identity  實際環境（type_id | name，例如 VScode / Chrome）
    environment_setting   設定字典（permission / delegate / mode / models ...）
    environment_hotkey    設定 × 熱鍵對應（setting_id | hotkey）
    keyboard_button       鍵盤按鈕字典（Ctrl / Alt / . / K / F2 ...）
    environment_setting_option  設定選項字典（default / autopilot / allow all ...）
    environment_setting_value    設定 × 選項對應（setting_id | option_id）

用法：
    from environment import Environment
    e = Environment()
    e.list_types()
    e.close()
"""

from .api import Environment

__all__ = ["Environment"]
__version__ = "1.0.0"
