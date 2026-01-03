"""进度追踪器实现"""

from typing import List
from .models import ProgressReport


class ProgressTracker:
    """翻译进度追踪"""
    
    def calculate_progress(self, source_dir: str, target_dir: str) -> ProgressReport:
        """计算翻译进度
        
        Args:
            source_dir: 源文件目录 (en-US)
            target_dir: 目标文件目录 (zh_Hans)
            
        Returns:
            ProgressReport: 进度报告
        """
        # TODO: 实现进度计算
        raise NotImplementedError("Will be implemented in Task 9.1")
    
    def get_untranslated_entries(self, compendium: str) -> List[str]:
        """获取未翻译的条目列表
        
        Args:
            compendium: Compendium 名称
            
        Returns:
            List[str]: 未翻译条目的 key 列表
        """
        # TODO: 实现未翻译条目获取
        raise NotImplementedError("Will be implemented in Task 9.1")
    
    def get_outdated_entries(self, compendium: str) -> List[str]:
        """获取需要更新的条目列表
        
        Args:
            compendium: Compendium 名称
            
        Returns:
            List[str]: 需要更新条目的 key 列表
        """
        # TODO: 实现过期条目获取
        raise NotImplementedError("Will be implemented in Task 9.3")
    
    def generate_dashboard(self) -> str:
        """生成进度仪表板 (Markdown 格式)
        
        Returns:
            str: Markdown 格式的进度仪表板
        """
        # TODO: 实现仪表板生成
        raise NotImplementedError("Will be implemented in Task 9.5")
