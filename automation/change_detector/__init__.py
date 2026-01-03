"""变更检测模块 - 检测源文件变更，生成变更报告"""

from .detector import ChangeDetector
from .models import ChangeReport

__all__ = ["ChangeDetector", "ChangeReport"]
