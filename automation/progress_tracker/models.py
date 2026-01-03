"""进度追踪数据模型"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class EntryStatus:
    """单个条目的状态"""
    
    key: str
    is_translated: bool = False
    is_outdated: bool = False
    source_hash: Optional[str] = None
    translation_hash: Optional[str] = None
    last_modified: Optional[str] = None


@dataclass
class CompendiumProgress:
    """单个 Compendium 的进度数据"""
    
    name: str
    total: int = 0
    translated: int = 0
    untranslated: int = 0
    outdated: int = 0
    untranslated_entries: List[str] = field(default_factory=list)
    outdated_entries: List[str] = field(default_factory=list)
    
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
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def completion_percentage(self) -> float:
        """总体完成百分比"""
        if self.total_entries == 0:
            return 0.0
        return (self.translated_entries / self.total_entries) * 100
    
    def get_all_untranslated_entries(self) -> Dict[str, List[str]]:
        """获取所有未翻译条目，按 compendium 分组"""
        return {
            name: progress.untranslated_entries 
            for name, progress in self.by_compendium.items()
            if progress.untranslated_entries
        }
    
    def get_all_outdated_entries(self) -> Dict[str, List[str]]:
        """获取所有需要更新的条目，按 compendium 分组"""
        return {
            name: progress.outdated_entries 
            for name, progress in self.by_compendium.items()
            if progress.outdated_entries
        }
