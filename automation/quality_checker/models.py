"""质量检查数据模型"""

import json
from dataclasses import dataclass, field
from typing import List, Literal, Dict, Any
from datetime import datetime


@dataclass
class Issue:
    """质量问题数据类"""
    
    severity: Literal["error", "warning", "info"]
    type: Literal["placeholder", "html", "uuid", "glossary"]
    message: str
    location: str  # entry key + field
    
    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.type}: {self.message} at {self.location}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "severity": self.severity,
            "type": self.type,
            "message": self.message,
            "location": self.location
        }


@dataclass
class QualityReport:
    """质量报告数据类"""
    
    file_name: str
    issues: List[Issue] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
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
    
    @property
    def has_issues(self) -> bool:
        """是否有任何问题"""
        return len(self.issues) > 0
    
    def issues_by_type(self) -> Dict[str, List[Issue]]:
        """按类型分组问题"""
        grouped: Dict[str, List[Issue]] = {}
        for issue in self.issues:
            if issue.type not in grouped:
                grouped[issue.type] = []
            grouped[issue.type].append(issue)
        return grouped
    
    def issues_by_severity(self) -> Dict[str, List[Issue]]:
        """按严重程度分组问题"""
        grouped: Dict[str, List[Issue]] = {}
        for issue in self.issues:
            if issue.severity not in grouped:
                grouped[issue.severity] = []
            grouped[issue.severity].append(issue)
        return grouped
    
    def issues_by_location(self) -> Dict[str, List[Issue]]:
        """按位置分组问题"""
        grouped: Dict[str, List[Issue]] = {}
        for issue in self.issues:
            if issue.location not in grouped:
                grouped[issue.location] = []
            grouped[issue.location].append(issue)
        return grouped
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "file_name": self.file_name,
            "generated_at": self.generated_at,
            "summary": {
                "total": len(self.issues),
                "errors": self.error_count,
                "warnings": self.warning_count,
                "info": self.info_count
            },
            "issues": [issue.to_dict() for issue in self.issues]
        }
    
    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON 字符串
        
        Args:
            indent: 缩进空格数
            
        Returns:
            str: JSON 字符串
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
    
    def to_markdown(self) -> str:
        """转换为 Markdown 格式
        
        Returns:
            str: Markdown 字符串
        """
        lines = []
        
        # 标题
        lines.append(f"# 质量检查报告: {self.file_name}")
        lines.append("")
        lines.append(f"生成时间: {self.generated_at}")
        lines.append("")
        
        # 摘要
        lines.append("## 摘要")
        lines.append("")
        lines.append(f"- 总问题数: {len(self.issues)}")
        lines.append(f"- 错误: {self.error_count}")
        lines.append(f"- 警告: {self.warning_count}")
        lines.append(f"- 信息: {self.info_count}")
        lines.append("")
        
        if not self.issues:
            lines.append("✅ 未发现任何问题！")
            return "\n".join(lines)
        
        # 按严重程度分组
        lines.append("## 问题详情")
        lines.append("")
        
        by_severity = self.issues_by_severity()
        
        # 先显示错误
        if "error" in by_severity:
            lines.append("### ❌ 错误")
            lines.append("")
            for issue in by_severity["error"]:
                lines.append(f"- **[{issue.type}]** {issue.message}")
                lines.append(f"  - 位置: `{issue.location}`")
            lines.append("")
        
        # 然后显示警告
        if "warning" in by_severity:
            lines.append("### ⚠️ 警告")
            lines.append("")
            for issue in by_severity["warning"]:
                lines.append(f"- **[{issue.type}]** {issue.message}")
                lines.append(f"  - 位置: `{issue.location}`")
            lines.append("")
        
        # 最后显示信息
        if "info" in by_severity:
            lines.append("### ℹ️ 信息")
            lines.append("")
            for issue in by_severity["info"]:
                lines.append(f"- **[{issue.type}]** {issue.message}")
                lines.append(f"  - 位置: `{issue.location}`")
            lines.append("")
        
        return "\n".join(lines)
