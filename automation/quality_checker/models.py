"""质量检查数据模型"""

from dataclasses import dataclass, field
from typing import List, Literal


@dataclass
class Issue:
    """质量问题数据类"""
    
    severity: Literal["error", "warning", "info"]
    type: Literal["placeholder", "html", "uuid", "glossary"]
    message: str
    location: str  # entry key + field
    
    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.type}: {self.message} at {self.location}"


@dataclass
class QualityReport:
    """质量报告数据类"""
    
    file_name: str
    issues: List[Issue] = field(default_factory=list)
    
    @property
    def error_count(self) -> int:
        """错误数量"""
        return sum(1 for i in self.issues if i.severity == "error")
    
    @property
    def warning_count(self) -> int:
        """警告数量"""
        return sum(1 for i in self.issues if i.severity == "warning")
    
    @property
    def info_count(self) -> int:
        """信息数量"""
        return sum(1 for i in self.issues if i.severity == "info")
    
    @property
    def has_errors(self) -> bool:
        """是否有错误"""
        return self.error_count > 0
