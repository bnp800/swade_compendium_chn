"""格式转换模块 - 处理 Babele JSON 与 Weblate 友好格式之间的转换

支持的功能:
- HTML 文本提取，保留结构信息
- UUID/Compendium 链接占位符处理
- 多格式输出 (PO, CSV, JSON)
- 翻译注入，保持 HTML 结构完整
"""

from .converter import (
    FormatConverter,
    ExtractedEntry,
    HTMLTextExtractor,
    LinkPlaceholderManager,
    extract_for_weblate,
    inject_translations,
)

__all__ = [
    "FormatConverter",
    "ExtractedEntry",
    "HTMLTextExtractor",
    "LinkPlaceholderManager",
    "extract_for_weblate",
    "inject_translations",
]
