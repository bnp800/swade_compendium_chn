"""多模块支持组件

提供跨模块翻译管理功能，包括：
- 模块结构自动创建
- 跨模块翻译复用
- 共享内容检测
"""

from .manager import MultiModuleManager

__all__ = ["MultiModuleManager"]
