"""增量更新组件

提供增量更新功能，保留未变更条目的现有翻译，只处理新增和修改的条目。
"""

from .updater import IncrementalUpdater

__all__ = ["IncrementalUpdater"]
