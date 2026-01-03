"""变更检测数据模型"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ChangeReport:
    """变更报告数据类"""
    
    file_name: str
    added_entries: List[str] = field(default_factory=list)
    modified_entries: List[str] = field(default_factory=list)
    deleted_entries: List[str] = field(default_factory=list)
    unchanged_entries: List[str] = field(default_factory=list)
    
    @property
    def has_changes(self) -> bool:
        """检查是否有任何变更"""
        return bool(self.added_entries or self.modified_entries or self.deleted_entries)
    
    @property
    def total_entries(self) -> int:
        """返回所有条目的总数"""
        return (
            len(self.added_entries) +
            len(self.modified_entries) +
            len(self.deleted_entries) +
            len(self.unchanged_entries)
        )
