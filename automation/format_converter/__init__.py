"""格式转换模块 - 处理 Babele JSON 与翻译者友好格式之间的转换

核心流程（CSV 优先 + 链接剥离）:
- HTML 文本提取，完全剥离链接和 HTML 标签
- CSV 为主要输出格式（UTF-8 BOM），JSON 为辅助格式
- 翻译注入，保持 HTML 结构完整，保留原始链接
"""

from .converter import (
    FormatConverter,
    ExtractedEntry,
    HTMLTextExtractor,
    LinkPlaceholderManager,
    LinkInfo,
    extract_for_translation,
    extract_for_weblate,
    inject_translations,
)

__all__ = [
    "FormatConverter",
    "ExtractedEntry",
    "HTMLTextExtractor",
    "LinkPlaceholderManager",
    "LinkInfo",
    "extract_for_translation",
    "extract_for_weblate",
    "inject_translations",
]
