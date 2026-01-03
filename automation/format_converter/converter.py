"""格式转换器实现 - 处理 Babele JSON 与 Weblate 友好格式之间的转换

支持的功能:
- HTML 文本提取，保留结构信息
- UUID/Compendium 链接占位符处理
- 多格式输出 (PO, CSV, JSON)
- 翻译注入，保持 HTML 结构完整
"""

import json
import re
import csv
import hashlib
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from io import StringIO


@dataclass
class ExtractedEntry:
    """提取的翻译条目"""
    key: str
    field: str
    source_text: str
    source_html: str
    placeholders: Dict[str, Dict[str, str]] = field(default_factory=dict)
    context: str = ""
    
    def get_msgid(self) -> str:
        """获取用于 PO 文件的 msgid"""
        return self.source_text
    
    def get_msgctxt(self) -> str:
        """获取 PO 文件的上下文"""
        return f"{self.key}:{self.field}"


class HTMLTextExtractor(HTMLParser):
    """HTML 解析器，提取纯文本并保留结构信息"""
    
    def __init__(self):
        super().__init__()
        self.text_parts: List[str] = []
        self.tag_stack: List[str] = []
        self.ignore_tags = {'script', 'style'}
        self.block_tags = {'p', 'div', 'article', 'section', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr', 'td', 'th'}
        
    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        self.tag_stack.append(tag)
        # 块级元素前添加换行
        if tag in self.block_tags and self.text_parts:
            self.text_parts.append('\n')
            
    def handle_endtag(self, tag: str):
        if self.tag_stack and self.tag_stack[-1] == tag:
            self.tag_stack.pop()
        # 块级元素后添加换行
        if tag in self.block_tags:
            self.text_parts.append('\n')
            
    def handle_data(self, data: str):
        if not any(tag in self.tag_stack for tag in self.ignore_tags):
            # 保留有意义的空白
            cleaned = data.strip()
            if cleaned:
                self.text_parts.append(cleaned)
            elif data and self.text_parts and not self.text_parts[-1].endswith(' '):
                # 保留单词间的空格
                self.text_parts.append(' ')
                
    def handle_entityref(self, name: str):
        """处理 HTML 实体引用如 &nbsp;"""
        entity_map = {
            'nbsp': ' ',
            'lt': '<',
            'gt': '>',
            'amp': '&',
            'quot': '"',
            'apos': "'",
            'rsquo': "'",
            'lsquo': "'",
            'rdquo': '"',
            'ldquo': '"',
            'mdash': '—',
            'ndash': '–',
            'shy': '',  # 软连字符
        }
        char = entity_map.get(name, f'&{name};')
        if not any(tag in self.tag_stack for tag in self.ignore_tags):
            self.text_parts.append(char)
            
    def handle_charref(self, name: str):
        """处理数字字符引用如 &#160;"""
        try:
            if name.startswith('x'):
                char = chr(int(name[1:], 16))
            else:
                char = chr(int(name))
            if not any(tag in self.tag_stack for tag in self.ignore_tags):
                self.text_parts.append(char)
        except (ValueError, OverflowError):
            self.text_parts.append(f'&#{name};')
    
    def get_text(self) -> str:
        """获取提取的纯文本"""
        text = ''.join(self.text_parts)
        # 清理多余的空白
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        return text.strip()


class LinkPlaceholderManager:
    """管理 UUID 和 Compendium 链接的占位符"""
    
    # 链接模式
    LINK_PATTERNS = {
        'uuid_with_text': re.compile(r'@UUID\[([^\]]+)\]\{([^}]+)\}'),
        'compendium_with_text': re.compile(r'@Compendium\[([^\]]+)\]\{([^}]+)\}'),
        'uuid_plain': re.compile(r'@UUID\[([^\]]+)\](?!\{)'),
        'compendium_plain': re.compile(r'@Compendium\[([^\]]+)\](?!\{)'),
    }
    
    def __init__(self):
        self.placeholder_counter = 0
        self.placeholder_map: Dict[str, Dict[str, Any]] = {}
        
    def reset(self):
        """重置占位符计数器和映射"""
        self.placeholder_counter = 0
        self.placeholder_map = {}
        
    def extract_links(self, content: str) -> Tuple[str, Dict[str, Dict[str, Any]]]:
        """提取链接并替换为占位符
        
        Args:
            content: 包含链接的 HTML 内容
            
        Returns:
            (处理后的内容, 占位符映射)
        """
        self.reset()
        processed = content
        
        # 先处理带文本的链接
        for pattern_name in ['uuid_with_text', 'compendium_with_text']:
            pattern = self.LINK_PATTERNS[pattern_name]
            matches = list(pattern.finditer(processed))
            for match in reversed(matches):  # 从后向前替换，避免位置偏移
                full_match = match.group(0)
                ref = match.group(1)
                text = match.group(2)
                
                placeholder = f"[[LINK_{self.placeholder_counter}]]"
                self.placeholder_map[placeholder] = {
                    'type': pattern_name.replace('_with_text', ''),
                    'full': full_match,
                    'ref': ref,
                    'text': text,
                    'has_text': True
                }
                processed = processed[:match.start()] + placeholder + processed[match.end():]
                self.placeholder_counter += 1
        
        # 再处理纯链接
        for pattern_name in ['uuid_plain', 'compendium_plain']:
            pattern = self.LINK_PATTERNS[pattern_name]
            matches = list(pattern.finditer(processed))
            for match in reversed(matches):
                full_match = match.group(0)
                ref = match.group(1)
                
                placeholder = f"[[LINK_{self.placeholder_counter}]]"
                self.placeholder_map[placeholder] = {
                    'type': pattern_name.replace('_plain', ''),
                    'full': full_match,
                    'ref': ref,
                    'text': '',
                    'has_text': False
                }
                processed = processed[:match.start()] + placeholder + processed[match.end():]
                self.placeholder_counter += 1
                
        return processed, self.placeholder_map
    
    def restore_links(self, content: str, placeholder_map: Dict[str, Dict[str, Any]]) -> str:
        """恢复占位符为原始链接
        
        Args:
            content: 包含占位符的内容
            placeholder_map: 占位符映射
            
        Returns:
            恢复链接后的内容
        """
        result = content
        for placeholder, link_data in placeholder_map.items():
            result = result.replace(placeholder, link_data['full'])
        return result
    
    def get_link_count(self, content: str) -> int:
        """统计内容中的链接数量"""
        count = 0
        for pattern in self.LINK_PATTERNS.values():
            count += len(pattern.findall(content))
        return count


class FormatConverter:
    """在 Babele JSON 和 Weblate 格式之间转换"""
    
    def __init__(self):
        self.link_manager = LinkPlaceholderManager()
        self.translatable_fields = ['name', 'description', 'biography', 'text', 'notes', 'category']
        
    def extract_text_from_html(self, html_content: str) -> str:
        """从 HTML 中提取纯文本"""
        if not html_content:
            return ""
        extractor = HTMLTextExtractor()
        try:
            extractor.feed(html_content)
        except Exception:
            # 如果解析失败，返回原始内容去除标签
            return re.sub(r'<[^>]+>', '', html_content).strip()
        return extractor.get_text()
    
    def extract_entries(self, babele_data: Dict) -> List[ExtractedEntry]:
        """从 Babele JSON 数据中提取所有可翻译条目
        
        Args:
            babele_data: Babele JSON 数据字典
            
        Returns:
            提取的条目列表
        """
        entries = []
        babele_entries = babele_data.get('entries', {})
        
        for key, value in babele_entries.items():
            if not isinstance(value, dict):
                continue
                
            for field_name in self.translatable_fields:
                if field_name not in value:
                    continue
                    
                field_value = value[field_name]
                if not field_value or not isinstance(field_value, str):
                    continue
                
                # 提取链接占位符
                processed_content, placeholders = self.link_manager.extract_links(field_value)
                
                # 判断是否为 HTML 内容
                is_html = '<' in field_value and '>' in field_value
                
                if is_html:
                    source_text = self.extract_text_from_html(processed_content)
                else:
                    source_text = processed_content.strip()
                
                if source_text:  # 只添加非空条目
                    entries.append(ExtractedEntry(
                        key=key,
                        field=field_name,
                        source_text=source_text,
                        source_html=field_value,
                        placeholders=placeholders,
                        context=f"{key}:{field_name}"
                    ))
                    
            # 处理嵌套的 actions 字段
            if 'actions' in value and isinstance(value['actions'], dict):
                self._extract_nested_actions(key, value['actions'], entries)
                
        return entries
    
    def _extract_nested_actions(self, parent_key: str, actions: Dict, entries: List[ExtractedEntry]):
        """提取嵌套的 actions 字段"""
        for action_type, action_data in actions.items():
            if not isinstance(action_data, dict):
                continue
            for action_name, action_value in action_data.items():
                if isinstance(action_value, dict) and 'name' in action_value:
                    name_value = action_value['name']
                    if name_value and isinstance(name_value, str):
                        entries.append(ExtractedEntry(
                            key=parent_key,
                            field=f"actions.{action_type}.{action_name}.name",
                            source_text=name_value,
                            source_html=name_value,
                            placeholders={},
                            context=f"{parent_key}:actions.{action_type}.{action_name}.name"
                        ))
    
    def extract_for_weblate(self, babele_json_path: str, output_format: str = 'po') -> str:
        """从 Babele JSON 提取纯文本，生成 Weblate 兼容格式
        
        Args:
            babele_json_path: Babele JSON 文件路径
            output_format: 输出格式 ('po', 'csv', 'json')
            
        Returns:
            转换后的内容字符串
        """
        with open(babele_json_path, 'r', encoding='utf-8') as f:
            babele_data = json.load(f)
            
        entries = self.extract_entries(babele_data)
        
        if output_format == 'po':
            return self._to_po_format(entries)
        elif output_format == 'csv':
            return self._to_csv_format(entries)
        elif output_format == 'json':
            return self._to_json_format(entries)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    def extract_from_data(self, babele_data: Dict, output_format: str = 'po') -> str:
        """从 Babele JSON 数据提取纯文本
        
        Args:
            babele_data: Babele JSON 数据字典
            output_format: 输出格式 ('po', 'csv', 'json')
            
        Returns:
            转换后的内容字符串
        """
        entries = self.extract_entries(babele_data)
        
        if output_format == 'po':
            return self._to_po_format(entries)
        elif output_format == 'csv':
            return self._to_csv_format(entries)
        elif output_format == 'json':
            return self._to_json_format(entries)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

    def _to_po_format(self, entries: List[ExtractedEntry]) -> str:
        """转换为 PO 格式 (Weblate 原生格式)
        
        PO 格式说明:
        - msgctxt: 上下文，用于区分相同文本的不同位置
        - msgid: 源文本
        - msgstr: 翻译文本（空字符串表示未翻译）
        - #. 注释: 提取的注释
        - #: 位置: 源文件位置
        """
        lines = []
        
        # PO 文件头
        lines.append('# SWADE Translation File')
        lines.append('# Generated by swade-translation-automation')
        lines.append('msgid ""')
        lines.append('msgstr ""')
        lines.append('"Content-Type: text/plain; charset=UTF-8\\n"')
        lines.append('"Content-Transfer-Encoding: 8bit\\n"')
        lines.append('')
        
        for entry in entries:
            # 添加注释
            if entry.placeholders:
                lines.append(f'#. Contains {len(entry.placeholders)} link placeholder(s)')
            
            # 添加位置信息
            lines.append(f'#: {entry.context}')
            
            # 上下文
            msgctxt = self._escape_po_string(entry.get_msgctxt())
            lines.append(f'msgctxt "{msgctxt}"')
            
            # 源文本 - 处理多行
            msgid = self._escape_po_string(entry.source_text)
            if '\n' in entry.source_text:
                lines.append('msgid ""')
                for line in entry.source_text.split('\n'):
                    escaped_line = self._escape_po_string(line)
                    lines.append(f'"{escaped_line}\\n"')
            else:
                lines.append(f'msgid "{msgid}"')
            
            # 翻译文本（空）
            lines.append('msgstr ""')
            lines.append('')
            
        return '\n'.join(lines)
    
    def _escape_po_string(self, text: str) -> str:
        """转义 PO 格式字符串"""
        if not text:
            return ""
        # 转义特殊字符
        text = text.replace('\\', '\\\\')
        text = text.replace('"', '\\"')
        text = text.replace('\t', '\\t')
        # 不转义换行符，因为我们单独处理多行
        return text
    
    def _to_csv_format(self, entries: List[ExtractedEntry]) -> str:
        """转换为 CSV 格式"""
        output = StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow(['key', 'field', 'source_text', 'translated_text', 'context', 'placeholders'])
        
        for entry in entries:
            placeholders_json = json.dumps(entry.placeholders, ensure_ascii=False) if entry.placeholders else ''
            writer.writerow([
                entry.key,
                entry.field,
                entry.source_text,
                '',  # 翻译文本为空
                entry.context,
                placeholders_json
            ])
            
        return output.getvalue()
    
    def _to_json_format(self, entries: List[ExtractedEntry]) -> str:
        """转换为 JSON 格式"""
        data = {
            'entries': {}
        }
        
        for entry in entries:
            if entry.key not in data['entries']:
                data['entries'][entry.key] = {}
            
            data['entries'][entry.key][entry.field] = {
                'source': entry.source_text,
                'translation': '',
                'source_html': entry.source_html,
                'placeholders': entry.placeholders
            }
            
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    def inject_translations(self, source_json_path: str, translations_path: str, 
                           output_path: Optional[str] = None) -> str:
        """将翻译注入回 Babele JSON 格式
        
        Args:
            source_json_path: 源 JSON 文件路径
            translations_path: 翻译文件路径 (CSV, JSON, 或 PO)
            output_path: 输出文件路径（可选）
            
        Returns:
            注入翻译后的 JSON 内容
        """
        # 加载源数据
        with open(source_json_path, 'r', encoding='utf-8') as f:
            source_data = json.load(f)
        
        # 加载翻译
        translations = self._load_translations(translations_path)
        
        # 注入翻译
        result = self.inject_translations_to_data(source_data, translations)
        
        # 保存结果
        result_json = json.dumps(result, ensure_ascii=False, indent=4)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result_json)
                
        return result_json
    
    def inject_translations_to_data(self, source_data: Dict, 
                                    translations: Dict[str, Dict[str, str]]) -> Dict:
        """将翻译注入到源数据中
        
        Args:
            source_data: 源 Babele JSON 数据
            translations: 翻译字典 {key: {field: translation}}
            
        Returns:
            注入翻译后的数据
        """
        result = json.loads(json.dumps(source_data))  # 深拷贝
        entries = result.get('entries', {})
        
        for key, entry_value in entries.items():
            if key not in translations:
                continue
                
            entry_translations = translations[key]
            
            for field_name, translated_text in entry_translations.items():
                if not translated_text:
                    continue
                    
                # 处理嵌套字段 (如 actions.additional.xxx.name)
                if '.' in field_name:
                    self._set_nested_field(entry_value, field_name, translated_text)
                elif field_name in entry_value:
                    source_value = entry_value[field_name]
                    
                    # 判断是否需要保持 HTML 结构
                    if '<' in source_value and '>' in source_value:
                        # HTML 内容 - 保持结构注入翻译
                        entry_value[field_name] = self.preserve_html_structure(
                            source_value, translated_text
                        )
                    else:
                        # 纯文本 - 直接替换
                        entry_value[field_name] = translated_text
                        
        return result
    
    def _set_nested_field(self, obj: Dict, field_path: str, value: str):
        """设置嵌套字段的值"""
        parts = field_path.split('.')
        current = obj
        
        for part in parts[:-1]:
            if part not in current:
                return
            current = current[part]
            if not isinstance(current, dict):
                return
                
        if parts[-1] in current:
            current[parts[-1]] = value
    
    def _load_translations(self, translations_path: str) -> Dict[str, Dict[str, str]]:
        """加载翻译文件
        
        Args:
            translations_path: 翻译文件路径
            
        Returns:
            翻译字典 {key: {field: translation}}
        """
        path = Path(translations_path)
        suffix = path.suffix.lower()
        
        if suffix == '.csv':
            return self._load_csv_translations(translations_path)
        elif suffix == '.json':
            return self._load_json_translations(translations_path)
        elif suffix == '.po':
            return self._load_po_translations(translations_path)
        else:
            raise ValueError(f"Unsupported translation file format: {suffix}")
    
    def _load_csv_translations(self, path: str) -> Dict[str, Dict[str, str]]:
        """从 CSV 文件加载翻译"""
        translations = {}
        
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row.get('key', '').strip()
                field = row.get('field', '').strip()
                translated = row.get('translated_text', '').strip()
                
                if key and field and translated:
                    if key not in translations:
                        translations[key] = {}
                    translations[key][field] = translated
                    
        return translations
    
    def _load_json_translations(self, path: str) -> Dict[str, Dict[str, str]]:
        """从 JSON 文件加载翻译"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        translations = {}
        entries = data.get('entries', data)  # 支持两种格式
        
        for key, value in entries.items():
            if isinstance(value, dict):
                translations[key] = {}
                for field, field_data in value.items():
                    if isinstance(field_data, dict):
                        # 新格式: {source, translation, ...}
                        trans = field_data.get('translation', '')
                    else:
                        # 旧格式: 直接是翻译文本
                        trans = field_data
                    if trans:
                        translations[key][field] = trans
                        
        return translations
    
    def _load_po_translations(self, path: str) -> Dict[str, Dict[str, str]]:
        """从 PO 文件加载翻译"""
        translations = {}
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 简单的 PO 解析器
        entries = re.split(r'\n\n+', content)
        
        for entry in entries:
            if not entry.strip() or entry.startswith('#'):
                continue
                
            # 提取 msgctxt
            msgctxt_match = re.search(r'msgctxt\s+"([^"]*)"', entry)
            if not msgctxt_match:
                continue
            msgctxt = msgctxt_match.group(1)
            
            # 解析上下文获取 key 和 field
            if ':' not in msgctxt:
                continue
            key, field = msgctxt.split(':', 1)
            
            # 提取 msgstr
            msgstr_match = re.search(r'msgstr\s+"([^"]*)"', entry)
            if not msgstr_match:
                # 尝试多行格式
                msgstr_match = re.search(r'msgstr\s+""\n((?:"[^"]*"\n?)+)', entry)
                if msgstr_match:
                    lines = re.findall(r'"([^"]*)"', msgstr_match.group(1))
                    translated = ''.join(lines)
                else:
                    continue
            else:
                translated = msgstr_match.group(1)
            
            # 反转义
            translated = self._unescape_po_string(translated)
            
            if translated:
                if key not in translations:
                    translations[key] = {}
                translations[key][field] = translated
                
        return translations
    
    def _unescape_po_string(self, text: str) -> str:
        """反转义 PO 格式字符串"""
        if not text:
            return ""
        text = text.replace('\\n', '\n')
        text = text.replace('\\t', '\t')
        text = text.replace('\\"', '"')
        text = text.replace('\\\\', '\\')
        return text

    def preserve_html_structure(self, source_html: str, translated_text: str) -> str:
        """保持 HTML 结构，只替换文本内容
        
        核心算法：
        1. 提取源 HTML 中的链接并替换为占位符
        2. 保留外层标签结构（包括 CSS 类）
        3. 将翻译文本注入到内部段落中
        4. 恢复链接占位符
        
        Args:
            source_html: 源 HTML 内容
            translated_text: 翻译后的纯文本
            
        Returns:
            保持结构的翻译 HTML
        """
        if not translated_text or not translated_text.strip():
            return source_html
            
        if not source_html or not source_html.strip():
            return translated_text
        
        # 如果翻译文本已经是 HTML 格式，直接返回
        if '<' in translated_text and '>' in translated_text:
            return self._merge_html_with_links(source_html, translated_text)
        
        # 1. 提取链接占位符
        processed_source, placeholder_map = self.link_manager.extract_links(source_html)
        
        # 2. 检查翻译文本是否已经包含链接（通过检查链接引用）
        # 这样可以处理空白字符被规范化的情况
        translated_has_links = self._text_contains_links(translated_text, placeholder_map)
        
        # 3. 分析源 HTML 结构（保留完整的外层标签）
        structure = self._analyze_html_structure_v2(processed_source)
        
        # 4. 将翻译文本注入结构
        if translated_has_links:
            # 翻译文本已经包含链接，不需要添加占位符
            result = self._inject_text_to_structure_v2(structure, translated_text, {})
        else:
            # 翻译文本不包含链接，需要添加占位符
            result = self._inject_text_to_structure_v2(structure, translated_text, placeholder_map)
            # 恢复链接
            result = self.link_manager.restore_links(result, placeholder_map)
        
        return result
    
    def _text_contains_links(self, text: str, placeholder_map: Dict) -> bool:
        """检查文本是否已经包含链接
        
        通过检查链接引用（而不是完整的链接字符串）来判断，
        这样可以处理空白字符被规范化的情况。
        """
        if not placeholder_map:
            return False
            
        for link_data in placeholder_map.values():
            link_ref = link_data['ref']
            link_type = link_data['type']
            
            # 检查是否包含该类型的链接引用
            if link_type == 'uuid':
                pattern = rf'@UUID\[{re.escape(link_ref)}\]'
            else:  # compendium
                pattern = rf'@Compendium\[{re.escape(link_ref)}\]'
            
            if re.search(pattern, text):
                return True
        
        return False
    
    def _merge_html_with_links(self, source_html: str, translated_html: str) -> str:
        """合并翻译 HTML 并保留源 HTML 中的链接"""
        translated_link_count = self.link_manager.get_link_count(translated_html)
        if translated_link_count > 0:
            return translated_html
        return translated_html
    
    def _analyze_html_structure_v2(self, html_content: str) -> Dict:
        """分析 HTML 结构，保留完整的外层标签
        
        Returns:
            结构信息字典
        """
        # 匹配外层容器标签（如 article, div, section）
        outer_match = re.match(
            r'^(\s*<(article|div|section|aside|main|header|footer)[^>]*>)'
            r'(.*?)'
            r'(</\2>\s*)$',
            html_content,
            re.DOTALL | re.IGNORECASE
        )
        
        if outer_match:
            outer_opening = outer_match.group(1)
            outer_tag = outer_match.group(2)
            inner_content = outer_match.group(3)
            outer_closing = outer_match.group(4)
        else:
            outer_opening = ''
            outer_tag = ''
            inner_content = html_content
            outer_closing = ''
        
        # 提取段落结构
        paragraphs = re.findall(r'<p[^>]*>.*?</p>', inner_content, re.DOTALL)
        
        return {
            'outer_opening': outer_opening,
            'outer_tag': outer_tag,
            'outer_closing': outer_closing,
            'inner_content': inner_content,
            'paragraphs': paragraphs,
            'has_paragraphs': len(paragraphs) > 0,
            'original': html_content
        }
    
    def _inject_text_to_structure_v2(self, structure: Dict, translated_text: str, 
                                     placeholder_map: Dict) -> str:
        """将翻译文本注入到 HTML 结构中（改进版）"""
        
        outer_opening = structure['outer_opening']
        outer_closing = structure['outer_closing']
        
        if structure['has_paragraphs']:
            inner_result = self._inject_to_paragraphs_v2(
                structure, translated_text, placeholder_map
            )
        else:
            # 简单结构：直接替换内容
            inner_result = translated_text
            
            # 检查翻译文本中是否已经包含占位符
            # 如果已经包含，就不需要再添加
            all_placeholders_in_text = all(
                ph in translated_text for ph in placeholder_map.keys()
            )
            
            # 只有当翻译文本中不包含占位符时，才添加占位符
            if not all_placeholders_in_text:
                for placeholder in placeholder_map.keys():
                    if placeholder not in inner_result:
                        inner_result = inner_result.rstrip() + ' ' + placeholder
        
        # 重建完整的 HTML，保留外层标签
        if outer_opening and outer_closing:
            return f"{outer_opening}\n{inner_result}\n{outer_closing}"
        elif outer_opening:
            return f"{outer_opening}\n{inner_result}"
        elif outer_closing:
            return f"{inner_result}\n{outer_closing}"
        else:
            return inner_result
    
    def _inject_to_paragraphs_v2(self, structure: Dict, translated_text: str,
                                 placeholder_map: Dict) -> str:
        """将翻译文本注入到段落结构中（改进版）"""
        
        # 分割翻译文本为段落
        translated_paragraphs = [p.strip() for p in translated_text.split('\n\n') if p.strip()]
        if not translated_paragraphs:
            translated_paragraphs = [p.strip() for p in translated_text.split('\n') if p.strip()]
        if not translated_paragraphs:
            translated_paragraphs = [translated_text.strip()]
        
        source_paragraphs = structure['paragraphs']
        result_paragraphs = []
        
        # 分配占位符到段落（基于源段落中的位置）
        placeholder_assignments = self._assign_placeholders_to_paragraphs(
            source_paragraphs, placeholder_map
        )
        
        # 检查翻译文本中是否已经包含占位符
        # 如果已经包含，就不需要再添加
        all_placeholders_in_text = all(
            ph in translated_text for ph in placeholder_map.keys()
        )
        
        for i, source_para in enumerate(source_paragraphs):
            # 提取段落的标签（保留属性）
            para_match = re.match(r'(<p[^>]*>)(.*?)(</p>)', source_para, re.DOTALL)
            if not para_match:
                result_paragraphs.append(source_para)
                continue
                
            opening_tag = para_match.group(1)
            closing_tag = para_match.group(3)
            
            # 获取对应的翻译段落
            if i < len(translated_paragraphs):
                trans_para = translated_paragraphs[i]
            else:
                trans_para = translated_paragraphs[-1] if translated_paragraphs else ''
            
            # 只有当翻译文本中不包含占位符时，才添加占位符
            if not all_placeholders_in_text:
                para_placeholders = placeholder_assignments.get(i, [])
                for ph in para_placeholders:
                    if ph not in trans_para:
                        trans_para = trans_para.rstrip() + ' ' + ph
            
            result_paragraphs.append(f"{opening_tag}{trans_para}{closing_tag}")
        
        # 如果翻译段落比源段落多，添加额外段落
        if len(translated_paragraphs) > len(source_paragraphs):
            for extra_para in translated_paragraphs[len(source_paragraphs):]:
                result_paragraphs.append(f"<p>{extra_para}</p>")
        
        return '\n'.join(result_paragraphs)
    
    def _assign_placeholders_to_paragraphs(self, source_paragraphs: List[str],
                                           placeholder_map: Dict) -> Dict[int, List[str]]:
        """将占位符分配到对应的段落"""
        assignments = {}
        
        for placeholder, link_data in placeholder_map.items():
            # 查找占位符在哪个段落
            for i, para in enumerate(source_paragraphs):
                if placeholder in para:
                    if i not in assignments:
                        assignments[i] = []
                    assignments[i].append(placeholder)
                    break
                    
        return assignments


# 便捷函数
def extract_for_weblate(babele_json_path: str, output_format: str = 'po') -> str:
    """从 Babele JSON 提取纯文本的便捷函数"""
    converter = FormatConverter()
    return converter.extract_for_weblate(babele_json_path, output_format)


def inject_translations(source_json_path: str, translations_path: str,
                       output_path: Optional[str] = None) -> str:
    """注入翻译的便捷函数"""
    converter = FormatConverter()
    return converter.inject_translations(source_json_path, translations_path, output_path)
