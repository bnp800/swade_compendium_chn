"""CLI 工具模块

提供命令行工具用于翻译验证和质量检查。
"""

from .validate import main as validate_main
from .quality_check import main as quality_check_main

__all__ = ["validate_main", "quality_check_main"]
