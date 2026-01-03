"""质量检查器实现"""

import re
from typing import List, Dict, Set, Optional
from .models import Issue, QualityReport


class QualityChecker:
    """翻译质量检查"""
    
    # 占位符模式
    # {0}, {1}, {name}, {{variable}}, %s, %d, etc.
    # Note: Order matters - more specific patterns should be matched first
    PLACEHOLDER_PATTERNS = [
        (r'\{\{(\w+)\}\}', True),    # {{variable}} - double braces (match first)
        (r'\{(\d+)\}', False),        # {0}, {1}, etc. - numeric
        (r'\{(\w+)\}', False),        # {name}, {variable}, etc. - single braces
        (r'%[sdifx]', False),         # %s, %d, %i, %f, %x
        (r'%\(\w+\)[sdifx]', False),  # %(name)s, %(count)d, etc.
    ]
    
    # HTML 自闭合标签
    SELF_CLOSING_TAGS = {
        'br', 'hr', 'img', 'input', 'meta', 'link', 'area', 
        'base', 'col', 'embed', 'param', 'source', 'track', 'wbr'
    }
    
    # UUID/Compendium 链接模式
    UUID_LINK_PATTERN = r'@UUID\[([^\]]+)\](?:\{([^}]*)\})?'
    COMPENDIUM_LINK_PATTERN = r'@Compendium\[([^\]]+)\](?:\{([^}]*)\})?'
    
    def __init__(self, location: str = ""):
        """初始化质量检查器
        
        Args:
            location: 当前检查位置（用于报告）
        """
        self.location = location
    
    def _extract_placeholders(self, text: str) -> Set[str]:
        """从文本中提取所有占位符
        
        Args:
            text: 要检查的文本
            
        Returns:
            Set[str]: 占位符集合
        """
        placeholders = set()
        # Track positions that have been matched to avoid overlapping matches
        matched_positions = set()
        
        for pattern, is_double_brace in self.PLACEHOLDER_PATTERNS:
            for match in re.finditer(pattern, text):
                start, end = match.start(), match.end()
                
                # Check if this position overlaps with an already matched position
                position_range = set(range(start, end))
                if position_range & matched_positions:
                    # Skip this match as it overlaps with a previous match
                    continue
                
                # Mark these positions as matched
                matched_positions.update(position_range)
                placeholders.add(match.group(0))
        
        return placeholders
    
    def check_placeholders(
        self, 
        source: str, 
        translation: str,
        location: Optional[str] = None
    ) -> List[Issue]:
        """检查占位符是否保持一致
        
        检测 {0}, {{variable}}, %s 等占位符，验证翻译中占位符完整性。
        
        Args:
            source: 源文本
            translation: 翻译文本
            location: 可选的位置信息
            
        Returns:
            List[Issue]: 问题列表
        """
        issues = []
        loc = location or self.location or "unknown"
        
        source_placeholders = self._extract_placeholders(source)
        translation_placeholders = self._extract_placeholders(translation)
        
        # 检查源文本中有但翻译中缺失的占位符
        missing = source_placeholders - translation_placeholders
        for placeholder in missing:
            issues.append(Issue(
                severity="error",
                type="placeholder",
                message=f"占位符 '{placeholder}' 在翻译中缺失",
                location=loc
            ))
        
        # 检查翻译中多出的占位符（可能是错误添加的）
        extra = translation_placeholders - source_placeholders
        for placeholder in extra:
            issues.append(Issue(
                severity="warning",
                type="placeholder",
                message=f"翻译中存在源文本没有的占位符 '{placeholder}'",
                location=loc
            ))
        
        return issues
    
    def check_html_tags(
        self, 
        source: str, 
        translation: str,
        location: Optional[str] = None
    ) -> List[Issue]:
        """检查 HTML 标签是否配对
        
        验证标签配对完整性，检测未闭合标签。
        
        Args:
            source: 源 HTML
            translation: 翻译 HTML
            location: 可选的位置信息
            
        Returns:
            List[Issue]: 问题列表
        """
        issues = []
        loc = location or self.location or "unknown"
        
        # 检查翻译文本的标签平衡
        tag_issues = self._check_tag_balance(translation, loc)
        issues.extend(tag_issues)
        
        # 比较源文本和翻译的标签结构
        source_tags = self._extract_tag_structure(source)
        translation_tags = self._extract_tag_structure(translation)
        
        if source_tags != translation_tags:
            issues.append(Issue(
                severity="warning",
                type="html",
                message=f"HTML 标签结构与源文本不一致。源: {source_tags}, 翻译: {translation_tags}",
                location=loc
            ))
        
        return issues
    
    def _check_tag_balance(self, html: str, location: str) -> List[Issue]:
        """检查 HTML 标签是否平衡
        
        Args:
            html: HTML 文本
            location: 位置信息
            
        Returns:
            List[Issue]: 问题列表
        """
        issues = []
        
        # 提取所有标签
        tag_pattern = r'<(/?)(\w+)([^>]*)(/?)>'
        stack = []
        
        for match in re.finditer(tag_pattern, html):
            is_closing = match.group(1) == '/'
            tag_name = match.group(2).lower()
            is_self_closing = match.group(4) == '/' or tag_name in self.SELF_CLOSING_TAGS
            
            if is_self_closing:
                continue
            
            if is_closing:
                if not stack:
                    issues.append(Issue(
                        severity="error",
                        type="html",
                        message=f"发现未匹配的闭合标签 '</{tag_name}>'",
                        location=location
                    ))
                elif stack[-1] != tag_name:
                    issues.append(Issue(
                        severity="error",
                        type="html",
                        message=f"标签不匹配: 期望 '</{stack[-1]}>' 但发现 '</{tag_name}>'",
                        location=location
                    ))
                    # 尝试恢复：如果栈中有匹配的标签，弹出到那里
                    if tag_name in stack:
                        while stack and stack[-1] != tag_name:
                            stack.pop()
                        if stack:
                            stack.pop()
                else:
                    stack.pop()
            else:
                stack.append(tag_name)
        
        # 检查未闭合的标签
        for unclosed_tag in stack:
            issues.append(Issue(
                severity="error",
                type="html",
                message=f"标签 '<{unclosed_tag}>' 未闭合",
                location=location
            ))
        
        return issues
    
    def _extract_tag_structure(self, html: str) -> List[str]:
        """提取 HTML 标签结构（用于比较）
        
        Args:
            html: HTML 文本
            
        Returns:
            List[str]: 标签列表（按顺序）
        """
        tag_pattern = r'<(/?)(\w+)([^>]*)(/?)>'
        tags = []
        
        for match in re.finditer(tag_pattern, html):
            is_closing = match.group(1) == '/'
            tag_name = match.group(2).lower()
            is_self_closing = match.group(4) == '/' or tag_name in self.SELF_CLOSING_TAGS
            
            if is_self_closing:
                tags.append(f"<{tag_name}/>")
            elif is_closing:
                tags.append(f"</{tag_name}>")
            else:
                tags.append(f"<{tag_name}>")
        
        return tags
    
    def _extract_uuid_links(self, text: str) -> Set[str]:
        """从文本中提取所有 UUID 和 Compendium 链接
        
        Args:
            text: 要检查的文本
            
        Returns:
            Set[str]: 链接集合（只包含 UUID/路径部分）
        """
        links = set()
        
        # 提取 @UUID[...] 链接
        for match in re.finditer(self.UUID_LINK_PATTERN, text):
            links.add(f"@UUID[{match.group(1)}]")
        
        # 提取 @Compendium[...] 链接
        for match in re.finditer(self.COMPENDIUM_LINK_PATTERN, text):
            links.add(f"@Compendium[{match.group(1)}]")
        
        return links
    
    def check_uuid_links(
        self, 
        source: str, 
        translation: str,
        location: Optional[str] = None
    ) -> List[Issue]:
        """检查 UUID 链接是否保持不变
        
        验证 UUID 链接在翻译前后保持一致。
        
        Args:
            source: 源文本
            translation: 翻译文本
            location: 可选的位置信息
            
        Returns:
            List[Issue]: 问题列表
        """
        issues = []
        loc = location or self.location or "unknown"
        
        source_links = self._extract_uuid_links(source)
        translation_links = self._extract_uuid_links(translation)
        
        # 检查缺失的链接
        missing = source_links - translation_links
        for link in missing:
            issues.append(Issue(
                severity="error",
                type="uuid",
                message=f"UUID/Compendium 链接 '{link}' 在翻译中缺失",
                location=loc
            ))
        
        # 检查多出的链接
        extra = translation_links - source_links
        for link in extra:
            issues.append(Issue(
                severity="warning",
                type="uuid",
                message=f"翻译中存在源文本没有的链接 '{link}'",
                location=loc
            ))
        
        return issues
    
    def check_glossary_consistency(
        self, 
        translation: str, 
        glossary: Dict[str, str],
        location: Optional[str] = None
    ) -> List[Issue]:
        """检查术语使用是否一致
        
        Args:
            translation: 翻译文本
            glossary: 术语表 (英文 -> 中文)
            location: 可选的位置信息
            
        Returns:
            List[Issue]: 问题列表
        """
        issues = []
        loc = location or self.location or "unknown"
        
        # 检查翻译中是否包含未翻译的英文术语
        for english_term, chinese_term in glossary.items():
            # 使用单词边界匹配英文术语
            pattern = r'\b' + re.escape(english_term) + r'\b'
            if re.search(pattern, translation, re.IGNORECASE):
                issues.append(Issue(
                    severity="warning",
                    type="glossary",
                    message=f"翻译中包含未翻译的术语 '{english_term}'，应翻译为 '{chinese_term}'",
                    location=loc
                ))
        
        return issues
    
    def check_all(
        self, 
        source: str, 
        translation: str,
        glossary: Optional[Dict[str, str]] = None,
        location: Optional[str] = None
    ) -> List[Issue]:
        """执行所有质量检查
        
        Args:
            source: 源文本
            translation: 翻译文本
            glossary: 可选的术语表
            location: 可选的位置信息
            
        Returns:
            List[Issue]: 所有问题列表
        """
        issues = []
        
        issues.extend(self.check_placeholders(source, translation, location))
        issues.extend(self.check_html_tags(source, translation, location))
        issues.extend(self.check_uuid_links(source, translation, location))
        
        if glossary:
            issues.extend(self.check_glossary_consistency(translation, glossary, location))
        
        return issues
    
    def generate_report(
        self, 
        issues: List[Issue],
        file_name: str = "unknown"
    ) -> QualityReport:
        """生成质量报告
        
        Args:
            issues: 问题列表
            file_name: 文件名
            
        Returns:
            QualityReport: 质量报告
        """
        return QualityReport(file_name=file_name, issues=issues)
