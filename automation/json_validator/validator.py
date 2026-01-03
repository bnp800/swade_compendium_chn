"""JSON 验证器实现

验证 JSON 文件语法正确性，报告错误位置。
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union


@dataclass
class JSONValidationError:
    """JSON 验证错误
    
    Attributes:
        file_path: 文件路径
        line: 错误行号（从1开始）
        column: 错误列号（从1开始）
        message: 错误消息
        error_type: 错误类型
    """
    file_path: str
    line: int
    column: int
    message: str
    error_type: str = "syntax"
    
    def __str__(self) -> str:
        return f"{self.file_path}:{self.line}:{self.column}: {self.error_type}: {self.message}"


@dataclass
class ValidationResult:
    """验证结果
    
    Attributes:
        file_path: 文件路径
        is_valid: 是否有效
        errors: 错误列表
    """
    file_path: str
    is_valid: bool
    errors: List[JSONValidationError] = field(default_factory=list)
    
    def __str__(self) -> str:
        if self.is_valid:
            return f"{self.file_path}: OK"
        error_strs = [str(e) for e in self.errors]
        return f"{self.file_path}: FAILED\n" + "\n".join(error_strs)


class JSONValidator:
    """JSON 文件验证器
    
    验证 JSON 文件语法正确性，支持：
    - 单文件验证
    - 目录批量验证
    - 详细错误位置报告
    """
    
    def __init__(self):
        """初始化验证器"""
        pass
    
    def _get_line_col_from_position(
        self, 
        content: str, 
        position: int
    ) -> tuple[int, int]:
        """从字符位置计算行号和列号
        
        Args:
            content: 文件内容
            position: 字符位置（从0开始）
            
        Returns:
            tuple[int, int]: (行号, 列号)，均从1开始
        """
        if position < 0:
            return (1, 1)
        
        lines = content[:position].split('\n')
        line = len(lines)
        col = len(lines[-1]) + 1 if lines else 1
        
        return (line, col)
    
    def _parse_json_error(
        self, 
        error: json.JSONDecodeError, 
        content: str,
        file_path: str
    ) -> JSONValidationError:
        """解析 JSON 解码错误
        
        Args:
            error: JSON 解码错误
            content: 文件内容
            file_path: 文件路径
            
        Returns:
            JSONValidationError: 验证错误
        """
        # JSONDecodeError 提供 lineno 和 colno
        line = error.lineno
        col = error.colno
        
        # 提取更友好的错误消息
        message = str(error.msg)
        
        # 尝试提供更具体的错误类型
        error_type = "syntax"
        if "Expecting" in message:
            error_type = "syntax"
        elif "Invalid" in message:
            error_type = "invalid_token"
        elif "Extra data" in message:
            error_type = "extra_data"
        elif "Unterminated" in message:
            error_type = "unterminated"
        
        return JSONValidationError(
            file_path=file_path,
            line=line,
            column=col,
            message=message,
            error_type=error_type
        )
    
    def validate_string(
        self, 
        content: str, 
        file_path: str = "<string>"
    ) -> ValidationResult:
        """验证 JSON 字符串
        
        Args:
            content: JSON 字符串内容
            file_path: 用于报告的文件路径
            
        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        
        try:
            json.loads(content)
            return ValidationResult(
                file_path=file_path,
                is_valid=True,
                errors=[]
            )
        except json.JSONDecodeError as e:
            error = self._parse_json_error(e, content, file_path)
            errors.append(error)
            return ValidationResult(
                file_path=file_path,
                is_valid=False,
                errors=errors
            )
        except Exception as e:
            # 处理其他异常
            errors.append(JSONValidationError(
                file_path=file_path,
                line=1,
                column=1,
                message=str(e),
                error_type="unknown"
            ))
            return ValidationResult(
                file_path=file_path,
                is_valid=False,
                errors=errors
            )
    
    def validate_file(self, file_path: Union[str, Path]) -> ValidationResult:
        """验证单个 JSON 文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            ValidationResult: 验证结果
        """
        path = Path(file_path)
        path_str = str(path)
        
        # 检查文件是否存在
        if not path.exists():
            return ValidationResult(
                file_path=path_str,
                is_valid=False,
                errors=[JSONValidationError(
                    file_path=path_str,
                    line=0,
                    column=0,
                    message=f"文件不存在: {path_str}",
                    error_type="file_not_found"
                )]
            )
        
        # 检查是否是文件
        if not path.is_file():
            return ValidationResult(
                file_path=path_str,
                is_valid=False,
                errors=[JSONValidationError(
                    file_path=path_str,
                    line=0,
                    column=0,
                    message=f"不是文件: {path_str}",
                    error_type="not_a_file"
                )]
            )
        
        # 读取并验证文件内容
        try:
            content = path.read_text(encoding='utf-8')
            return self.validate_string(content, path_str)
        except UnicodeDecodeError as e:
            return ValidationResult(
                file_path=path_str,
                is_valid=False,
                errors=[JSONValidationError(
                    file_path=path_str,
                    line=1,
                    column=1,
                    message=f"编码错误: {e}",
                    error_type="encoding"
                )]
            )
        except IOError as e:
            return ValidationResult(
                file_path=path_str,
                is_valid=False,
                errors=[JSONValidationError(
                    file_path=path_str,
                    line=0,
                    column=0,
                    message=f"读取文件失败: {e}",
                    error_type="io_error"
                )]
            )

    
    def validate_directory(
        self, 
        directory: Union[str, Path],
        pattern: str = "*.json",
        recursive: bool = True
    ) -> List[ValidationResult]:
        """验证目录中的所有 JSON 文件
        
        Args:
            directory: 目录路径
            pattern: 文件匹配模式
            recursive: 是否递归搜索子目录
            
        Returns:
            List[ValidationResult]: 验证结果列表
        """
        path = Path(directory)
        results = []
        
        if not path.exists():
            results.append(ValidationResult(
                file_path=str(path),
                is_valid=False,
                errors=[JSONValidationError(
                    file_path=str(path),
                    line=0,
                    column=0,
                    message=f"目录不存在: {path}",
                    error_type="directory_not_found"
                )]
            ))
            return results
        
        if not path.is_dir():
            results.append(ValidationResult(
                file_path=str(path),
                is_valid=False,
                errors=[JSONValidationError(
                    file_path=str(path),
                    line=0,
                    column=0,
                    message=f"不是目录: {path}",
                    error_type="not_a_directory"
                )]
            ))
            return results
        
        # 查找所有匹配的文件
        if recursive:
            files = list(path.rglob(pattern))
        else:
            files = list(path.glob(pattern))
        
        # 验证每个文件
        for file_path in sorted(files):
            result = self.validate_file(file_path)
            results.append(result)
        
        return results
    
    def validate_multiple_directories(
        self,
        directories: List[Union[str, Path]],
        pattern: str = "*.json",
        recursive: bool = True
    ) -> List[ValidationResult]:
        """验证多个目录中的 JSON 文件
        
        Args:
            directories: 目录路径列表
            pattern: 文件匹配模式
            recursive: 是否递归搜索子目录
            
        Returns:
            List[ValidationResult]: 验证结果列表
        """
        all_results = []
        
        for directory in directories:
            results = self.validate_directory(directory, pattern, recursive)
            all_results.extend(results)
        
        return all_results
    
    def generate_report(
        self, 
        results: List[ValidationResult],
        format: str = "text"
    ) -> str:
        """生成验证报告
        
        Args:
            results: 验证结果列表
            format: 报告格式 ("text", "markdown", "json")
            
        Returns:
            str: 报告内容
        """
        if format == "json":
            return self._generate_json_report(results)
        elif format == "markdown":
            return self._generate_markdown_report(results)
        else:
            return self._generate_text_report(results)
    
    def _generate_text_report(self, results: List[ValidationResult]) -> str:
        """生成文本格式报告"""
        lines = []
        
        valid_count = sum(1 for r in results if r.is_valid)
        invalid_count = len(results) - valid_count
        
        lines.append(f"JSON 验证报告")
        lines.append(f"=" * 50)
        lines.append(f"总文件数: {len(results)}")
        lines.append(f"有效: {valid_count}")
        lines.append(f"无效: {invalid_count}")
        lines.append("")
        
        if invalid_count > 0:
            lines.append("错误详情:")
            lines.append("-" * 50)
            for result in results:
                if not result.is_valid:
                    for error in result.errors:
                        lines.append(str(error))
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_markdown_report(self, results: List[ValidationResult]) -> str:
        """生成 Markdown 格式报告"""
        lines = []
        
        valid_count = sum(1 for r in results if r.is_valid)
        invalid_count = len(results) - valid_count
        
        lines.append("# JSON 验证报告")
        lines.append("")
        lines.append("## 摘要")
        lines.append("")
        lines.append(f"- **总文件数**: {len(results)}")
        lines.append(f"- **有效**: {valid_count}")
        lines.append(f"- **无效**: {invalid_count}")
        lines.append("")
        
        if invalid_count > 0:
            lines.append("## 错误详情")
            lines.append("")
            for result in results:
                if not result.is_valid:
                    lines.append(f"### {result.file_path}")
                    lines.append("")
                    for error in result.errors:
                        lines.append(f"- **行 {error.line}, 列 {error.column}**: {error.message}")
                    lines.append("")
        
        return "\n".join(lines)
    
    def _generate_json_report(self, results: List[ValidationResult]) -> str:
        """生成 JSON 格式报告"""
        import json
        
        report = {
            "summary": {
                "total": len(results),
                "valid": sum(1 for r in results if r.is_valid),
                "invalid": sum(1 for r in results if not r.is_valid)
            },
            "results": []
        }
        
        for result in results:
            result_dict = {
                "file": result.file_path,
                "valid": result.is_valid,
                "errors": []
            }
            for error in result.errors:
                result_dict["errors"].append({
                    "line": error.line,
                    "column": error.column,
                    "message": error.message,
                    "type": error.error_type
                })
            report["results"].append(result_dict)
        
        return json.dumps(report, ensure_ascii=False, indent=2)
