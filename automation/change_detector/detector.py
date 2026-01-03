"""变更检测器实现"""

from typing import List
from .models import ChangeReport


class ChangeDetector:
    """检测 en-US 目录中的文件变更"""
    
    def compare_files(self, old_file: str, new_file: str) -> ChangeReport:
        """比较两个 JSON 文件，返回变更报告
        
        Args:
            old_file: 旧文件路径
            new_file: 新文件路径
            
        Returns:
            ChangeReport: 变更报告
        """
        # TODO: 实现文件比较逻辑
        raise NotImplementedError("Will be implemented in Task 2.1")
    
    def detect_changes(self, source_dir: str) -> List[ChangeReport]:
        """检测目录中所有文件的变更
        
        Args:
            source_dir: 源目录路径
            
        Returns:
            List[ChangeReport]: 变更报告列表
        """
        # TODO: 实现目录变更检测
        raise NotImplementedError("Will be implemented in Task 2.1")
    
    def generate_changelog(self, changes: List[ChangeReport]) -> str:
        """生成人类可读的变更日志
        
        Args:
            changes: 变更报告列表
            
        Returns:
            str: Markdown 格式的变更日志
        """
        # TODO: 实现变更日志生成
        raise NotImplementedError("Will be implemented in Task 2.3")
