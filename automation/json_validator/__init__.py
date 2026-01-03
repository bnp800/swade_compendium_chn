"""JSON 验证器模块

提供 JSON 文件语法验证功能，支持错误位置报告。
"""

from .validator import JSONValidator, JSONValidationError, ValidationResult

__all__ = ["JSONValidator", "JSONValidationError", "ValidationResult"]
