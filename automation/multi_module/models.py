"""多模块支持数据模型"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class ModuleInfo:
    """模块信息"""
    
    id: str
    title: str
    compendiums: List[str] = field(default_factory=list)
    source_dir: Optional[str] = None
    target_dir: Optional[str] = None
    
    @property
    def file_prefix(self) -> str:
        """获取翻译文件前缀 (module_id.)"""
        return f"{self.id}."


@dataclass
class SharedContent:
    """共享内容信息"""
    
    entry_name: str
    source_module: str
    source_compendium: str
    target_modules: List[str] = field(default_factory=list)
    translation: Optional[Dict] = None
    
    @property
    def is_translated(self) -> bool:
        """检查是否已翻译"""
        if self.translation is None:
            return False
        name = self.translation.get("name", "")
        return bool(name) and name != self.entry_name


@dataclass
class TranslationReuse:
    """翻译复用记录"""
    
    entry_name: str
    source_module: str
    source_compendium: str
    target_module: str
    target_compendium: str
    translation: Dict = field(default_factory=dict)


@dataclass
class ModuleStructure:
    """模块翻译文件结构"""
    
    module_id: str
    source_files: List[str] = field(default_factory=list)
    target_files: List[str] = field(default_factory=list)
    missing_files: List[str] = field(default_factory=list)
    
    @property
    def is_complete(self) -> bool:
        """检查结构是否完整"""
        return len(self.missing_files) == 0


@dataclass
class ReuseReport:
    """翻译复用报告"""
    
    total_shared_entries: int = 0
    reused_translations: int = 0
    missing_translations: int = 0
    reuse_details: List[TranslationReuse] = field(default_factory=list)
    shared_content: List[SharedContent] = field(default_factory=list)
    
    @property
    def reuse_percentage(self) -> float:
        """计算复用率"""
        if self.total_shared_entries == 0:
            return 0.0
        return (self.reused_translations / self.total_shared_entries) * 100
