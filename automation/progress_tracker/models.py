"""进度追踪数据模型"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class CompendiumProgress:
    """单个 Compendium 的进度数据"""
    
    name: str
    total: int = 0
    translated: int = 0
    untranslated: int = 0
    outdated: int = 0
    
    @property
    def percentage(self) -> float:
        """翻译完成百分比"""
        if self.total == 0:
            return 0.0
        return (self.translated / self.total) * 100


@dataclass
class ProgressReport:
    """进度报告数据类"""
    
    total_entries: int = 0
    translated_entries: int = 0
    untranslated_entries: int = 0
    outdated_entries: int = 0
    by_compendium: Dict[str, CompendiumProgress] = field(default_factory=dict)
    
    @property
    def completion_percentage(self) -> float:
        """总体完成百分比"""
        if self.total_entries == 0:
            return 0.0
        return (self.translated_entries / self.total_entries) * 100
