"""格式转换器实现 - 处理 Babele JSON 与翻译者友好格式之间的转换

核心流程（CSV 优先 + 链接剥离）:
1. extract: Babele JSON → 剥离链接和HTML → 纯文本 CSV
2. inject:  翻译后的 CSV + 源 HTML 结构 → 半成品 JSON (链接待后处理)

设计要点:
- 提取阶段完全剥离 @UUID 和 @Compendium 链接，只保留显示文本作为上下文
- 剥离所有 HTML 标签，输出纯文本
- CSV 为主要输出格式（UTF-8 BOM），JSON 为辅助格式
- 注入阶段将纯文本翻译回填到源 HTML 结构中，链接保留英文原样
- 链接的翻译由 Link Post-Processor 在后处理阶段统一完成
"""

import json
import re
import csv
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from io import StringIO


@dataclass
class LinkInfo:
    """链接元数据，用于后处理阶段"""
    type: str           # 'uuid' 或 'compendium'
    ref: str            # 链接引用路径
    display_text: str   # 原始显示文本（英文）
    full_match: str     # 完整的链接字符串
    position: int       # 在文本中的大致位置


@dataclass
class ExtractedEntry:
    """提取的翻译条目"""
    key: str
    field: str
    source_text: str        # 纯文本，无链接无HTML
    source_html: str        # 原始 HTML（含链接）
    context: str = ""       # 上下文信息（含链接术语提示）
    link_display_texts: List[str] = field(default_factory=list)
    placeholders: Dict[str, Dict[str, str]] = field(default_factory=dict)

    def get_msgctxt(self) -> str:
        """获取上下文标识"""
        return f"{self.key}:{self.field}"


class HTMLTextExtractor(HTMLParser):
    """HTML 解析器，提取纯文本并保留结构信息"""

    def __init__(self):
        super().__init__()
        self.text_parts: List[str] = []
        self.tag_stack: List[str] = []
        self.ignore_tags = {'script', 'style'}
        self.block_tags = {'p', 'div', 'article', 'section', 'h1', 'h2', 'h3',
                          'h4', 'h5', 'h6', 'li', 'tr', 'td', 'th'}

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        self.tag_stack.append(tag)
        if tag in self.block_tags and self.text_parts:
            self.text_parts.append('\n')

    def handle_endtag(self, tag: str):
        if self.tag_stack and self.tag_stack[-1] == tag:
            self.tag_stack.pop()
        if tag in self.block_tags:
            self.text_parts.append('\n')

    def handle_data(self, data: str):
        if not any(tag in self.tag_stack for tag in self.ignore_tags):
            cleaned = data.strip()
            if cleaned:
                self.text_parts.append(cleaned)
            elif data and self.text_parts and not self.text_parts[-1].endswith(' '):
                self.text_parts.append(' ')

    def handle_entityref(self, name: str):
        """处理 HTML 实体引用如 &nbsp;"""
        entity_map = {
            'nbsp': ' ', 'lt': '<', 'gt': '>', 'amp': '&', 'quot': '"',
            'apos': "'", 'rsquo': '\u2019', 'lsquo': '\u2018',
            'rdquo': '\u201d', 'ldquo': '\u201c', 'mdash': '\u2014',
            'ndash': '\u2013', 'shy': '',
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
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        return text.strip()


class LinkPlaceholderManager:
    """管理 UUID 和 Compendium 链接的占位符

    支持两种模式:
    1. 占位符模式 (extract_links): 用占位符替换链接，用于注入时保留链接位置
    2. 剥离模式 (strip_links): 完全剥离链接，返回纯文本和链接元数据
    """

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
        """提取链接并替换为占位符（用于注入阶段保留链接位置）

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
            for match in reversed(matches):
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

    def strip_links(self, content: str) -> Tuple[str, List[LinkInfo]]:
        """从内容中完全剥离所有链接，返回纯文本和链接元数据

        链接处理规则:
        - @UUID[ref]{Display Text} → 完全移除，Display Text 记录到元数据
        - @Compendium[ref]{Display Text} → 完全移除，Display Text 记录到元数据
        - @UUID[ref] → 完全移除
        - @Compendium[ref] → 完全移除

        Args:
            content: 包含链接的内容

        Returns:
            (剥离链接后的文本, 链接信息列表)
        """
        links: List[LinkInfo] = []
        processed = content

        # 先处理带文本的链接
        for pattern_name in ['uuid_with_text', 'compendium_with_text']:
            pattern = self.LINK_PATTERNS[pattern_name]
            matches = list(pattern.finditer(processed))
            for match in reversed(matches):
                link_type = 'uuid' if 'uuid' in pattern_name else 'compendium'
                links.append(LinkInfo(
                    type=link_type,
                    ref=match.group(1),
                    display_text=match.group(2),
                    full_match=match.group(0),
                    position=match.start()
                ))
                # 完全移除链接
                processed = processed[:match.start()] + processed[match.end():]

        # 再处理纯链接
        for pattern_name in ['uuid_plain', 'compendium_plain']:
            pattern = self.LINK_PATTERNS[pattern_name]
            matches = list(pattern.finditer(processed))
            for match in reversed(matches):
                link_type = 'uuid' if 'uuid' in pattern_name else 'compendium'
                links.append(LinkInfo(
                    type=link_type,
                    ref=match.group(1),
                    display_text='',
                    full_match=match.group(0),
                    position=match.start()
                ))
                processed = processed[:match.start()] + processed[match.end():]

        # 清理多余空格
        processed = re.sub(r'  +', ' ', processed)

        return processed, links

    def restore_links(self, content: str, placeholder_map: Dict[str, Dict[str, Any]]) -> str:
        """恢复占位符为原始链接"""
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
    """在 Babele JSON 和翻译者友好格式之间转换

    核心流程：
    1. extract: Babele JSON → 剥离链接和HTML → 纯文本 CSV
    2. inject:  翻译后的 CSV + 源 HTML 结构 → 半成品 JSON (链接待后处理)
    """

    def __init__(self):
        self.link_manager = LinkPlaceholderManager()
        self.translatable_fields = ['name', 'description', 'biography', 'text',
                                    'notes', 'category']

    def extract_text_from_html(self, html_content: str) -> str:
        """从 HTML 中提取纯文本

        先剥离所有链接语法，再解析 HTML 标签提取文本。
        这确保链接语法不会被当作文本内容。
        """
        if not html_content:
            return ""
        # 先剥离链接，避免链接语法被当作文本
        stripped, _ = self.link_manager.strip_links(html_content)
        extractor = HTMLTextExtractor()
        try:
            extractor.feed(stripped)
        except Exception:
            return re.sub(r'<[^>]+>', '', stripped).strip()
        return extractor.get_text()

    def strip_links(self, html_content: str) -> Tuple[str, List[LinkInfo]]:
        """从 HTML 内容中剥离所有链接，返回纯文本和链接元数据

        @UUID[Compendium.xxx.yyy]{Display Text} → 完全移除
        @Compendium[xxx.yyy]{Display Text} → 完全移除
        @Compendium[xxx.yyy] → 完全移除（纯引用，无显示文本）

        Returns:
            (剥离链接后的文本, 链接信息列表)
        """
        return self.link_manager.strip_links(html_content)

    def extract_entries(self, babele_data: Dict) -> List[ExtractedEntry]:
        """从 Babele JSON 数据中提取所有可翻译条目

        提取逻辑（链接剥离模式）：
        1. 完全剥离 @UUID 和 @Compendium 链接
        2. 剥离 HTML 标签，输出纯文本
        3. 链接显示文本收集为上下文信息
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

                # 1. 剥离链接，收集链接元数据
                stripped_content, link_infos = self.strip_links(field_value)

                # 收集链接显示文本作为上下文
                link_display_texts = [li.display_text for li in link_infos
                                     if li.display_text]

                # 2. 判断是否为 HTML 内容并提取纯文本
                is_html = '<' in stripped_content and '>' in stripped_content
                if is_html:
                    # stripped_content already has links removed, just parse HTML
                    extractor = HTMLTextExtractor()
                    try:
                        extractor.feed(stripped_content)
                        source_text = extractor.get_text()
                    except Exception:
                        source_text = re.sub(r'<[^>]+>', '', stripped_content).strip()
                else:
                    source_text = stripped_content.strip()

                # 3. 构建上下文信息
                context = f"{key}:{field_name}"
                if link_display_texts:
                    context += f" | Contains links: {', '.join(link_display_texts)}"

                # 保留占位符映射（用于注入阶段）
                _, placeholders = self.link_manager.extract_links(field_value)

                if source_text:
                    entries.append(ExtractedEntry(
                        key=key,
                        field=field_name,
                        source_text=source_text,
                        source_html=field_value,
                        context=context,
                        link_display_texts=link_display_texts,
                        placeholders=placeholders,
                    ))

            # 处理嵌套的 actions 字段
            if 'actions' in value and isinstance(value['actions'], dict):
                self._extract_nested_actions(key, value['actions'], entries)

        return entries

    def _extract_nested_actions(self, parent_key: str, actions: Dict,
                                entries: List[ExtractedEntry]):
        """提取嵌套的 actions 字段"""
        for action_type, action_data in actions.items():
            if not isinstance(action_data, dict):
                continue
            for action_name, action_value in action_data.items():
                if isinstance(action_value, dict) and 'name' in action_value:
                    name_value = action_value['name']
                    if name_value and isinstance(name_value, str):
                        field_path = f"actions.{action_type}.{action_name}.name"
                        entries.append(ExtractedEntry(
                            key=parent_key,
                            field=field_path,
                            source_text=name_value,
                            source_html=name_value,
                            context=f"{parent_key}:{field_path}",
                            link_display_texts=[],
                            placeholders={},
                        ))

    def extract_for_translation(self, babele_json_path: str,
                                output_format: str = 'csv') -> str:
        """从 Babele JSON 提取纯文本，生成翻译者友好格式

        Args:
            babele_json_path: Babele JSON 文件路径
            output_format: 输出格式 ('csv' 或 'json')

        Returns:
            转换后的内容字符串
        """
        with open(babele_json_path, 'r', encoding='utf-8') as f:
            babele_data = json.load(f)

        entries = self.extract_entries(babele_data)

        if output_format == 'csv':
            return self._to_csv_format(entries)
        elif output_format == 'json':
            return self._to_json_format(entries)
        else:
            raise ValueError(f"Unsupported output format: {output_format}. "
                           f"Use 'csv' or 'json'.")

    # Keep backward-compatible alias
    def extract_for_weblate(self, babele_json_path: str,
                            output_format: str = 'csv') -> str:
        """向后兼容别名，调用 extract_for_translation"""
        return self.extract_for_translation(babele_json_path, output_format)

    def extract_from_data(self, babele_data: Dict,
                          output_format: str = 'csv') -> str:
        """从 Babele JSON 数据提取纯文本

        Args:
            babele_data: Babele JSON 数据字典
            output_format: 输出格式 ('csv' 或 'json')

        Returns:
            转换后的内容字符串
        """
        entries = self.extract_entries(babele_data)

        if output_format == 'csv':
            return self._to_csv_format(entries)
        elif output_format == 'json':
            return self._to_json_format(entries)
        else:
            raise ValueError(f"Unsupported output format: {output_format}. "
                           f"Use 'csv' or 'json'.")


    def _to_csv_format(self, entries: List[ExtractedEntry]) -> str:
        """转换为 CSV 格式（UTF-8 BOM，Excel/WPS 兼容）

        CSV 列: key, field, source_text, translated_text, context
        - source_text: 纯文本，无链接无HTML
        - context: 包含链接相关术语提示
        """
        output = StringIO()
        # UTF-8 BOM for Excel/WPS compatibility
        output.write('\ufeff')
        writer = csv.writer(output)

        # 写入表头
        writer.writerow(['key', 'field', 'source_text', 'translated_text', 'context'])

        for entry in entries:
            writer.writerow([
                entry.key,
                entry.field,
                entry.source_text,
                '',  # 翻译文本为空
                entry.context,
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
                'context': entry.context,
            }

        return json.dumps(data, ensure_ascii=False, indent=2)

    def inject_translations(self, source_json_path: str, translations_path: str,
                           output_path: Optional[str] = None) -> str:
        """将翻译注入回 Babele JSON 格式

        注入逻辑：将纯文本翻译注入回原始 HTML 结构，保留原始链接不变。
        输出半成品 JSON，链接仍为英文，待 Link Post-Processor 处理。

        Args:
            source_json_path: 源 JSON 文件路径
            translations_path: 翻译文件路径 (CSV 或 JSON)
            output_path: 输出文件路径（可选）

        Returns:
            注入翻译后的 JSON 内容
        """
        with open(source_json_path, 'r', encoding='utf-8') as f:
            source_data = json.load(f)

        translations = self._load_translations(translations_path)
        result = self.inject_translations_to_data(source_data, translations)
        result_json = json.dumps(result, ensure_ascii=False, indent=4)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result_json)

        return result_json

    def inject_translations_to_data(self, source_data: Dict,
                                    translations: Dict[str, Dict[str, str]]) -> Dict:
        """将翻译注入到源数据中

        保留原始链接不变，只替换文本内容。

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

                    if '<' in source_value and '>' in source_value:
                        # HTML 内容 - 保持结构注入翻译，保留原始链接
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
        else:
            raise ValueError(f"Unsupported translation file format: {suffix}. "
                           f"Use '.csv' or '.json'.")

    def _load_csv_translations(self, path: str) -> Dict[str, Dict[str, str]]:
        """从 CSV 文件加载翻译（支持 UTF-8 BOM）"""
        translations = {}

        with open(path, 'r', encoding='utf-8-sig') as f:
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
        entries = data.get('entries', data)

        for key, value in entries.items():
            if isinstance(value, dict):
                translations[key] = {}
                for field_name, field_data in value.items():
                    if isinstance(field_data, dict):
                        trans = field_data.get('translation', '')
                    else:
                        trans = field_data
                    if trans:
                        translations[key][field_name] = trans

        return translations


    def preserve_html_structure(self, source_html: str, translated_text: str) -> str:
        """保持 HTML 结构，只替换文本内容，保留原始链接不变

        核心算法：
        1. 提取源 HTML 中的链接并替换为占位符
        2. 保留外层标签结构（包括 CSS 类）
        3. 将翻译文本注入到内部段落中，保留占位符在原始位置
        4. 恢复链接占位符为原始链接

        Args:
            source_html: 源 HTML 内容（含链接）
            translated_text: 翻译后的纯文本（无链接无HTML）

        Returns:
            保持结构的翻译 HTML（链接保留英文原样，待后处理）
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

        # 2. 分析源 HTML 结构（已替换链接为占位符）
        structure = self._analyze_html_structure(processed_source)

        # 3. 将翻译文本注入结构，保留占位符在原始位置
        result = self._inject_text_to_structure(structure, translated_text, placeholder_map)

        # 4. 恢复链接
        result = self.link_manager.restore_links(result, placeholder_map)

        return result

    def _merge_html_with_links(self, source_html: str, translated_html: str) -> str:
        """合并翻译 HTML 并保留源 HTML 中的链接"""
        return translated_html

    def _analyze_html_structure(self, html_content: str) -> Dict:
        """分析 HTML 结构，保留完整的外层标签"""
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

    def _inject_text_to_structure(self, structure: Dict, translated_text: str,
                                  placeholder_map: Dict) -> str:
        """将翻译文本注入到 HTML 结构中

        关键：占位符保留在源段落的原始位置，翻译文本替换非占位符的文本部分。
        """
        outer_opening = structure['outer_opening']
        outer_closing = structure['outer_closing']

        if structure['has_paragraphs']:
            inner_result = self._inject_to_paragraphs(
                structure, translated_text, placeholder_map
            )
        else:
            # 无段落结构：将翻译文本与占位符组合
            inner_result = self._inject_text_with_placeholders(
                structure['inner_content'], translated_text, placeholder_map
            )

        if outer_opening and outer_closing:
            return f"{outer_opening}\n{inner_result}\n{outer_closing}"
        elif outer_opening:
            return f"{outer_opening}\n{inner_result}"
        elif outer_closing:
            return f"{inner_result}\n{outer_closing}"
        else:
            return inner_result

    def _inject_text_with_placeholders(self, source_content: str,
                                       translated_text: str,
                                       placeholder_map: Dict) -> str:
        """将翻译文本注入到包含占位符的内容中

        保留占位符在原始位置，用翻译文本替换其余文本。
        """
        # 找出源内容中占位符的位置
        placeholder_pattern = re.compile(r'\[\[LINK_\d+\]\]')
        parts = placeholder_pattern.split(source_content)
        placeholders_in_order = placeholder_pattern.findall(source_content)

        if not placeholders_in_order:
            # 无占位符，直接返回翻译文本
            return translated_text

        # 将翻译文本分配到非占位符的位置
        # 简单策略：将整个翻译文本放在第一个文本位置
        result_parts = []
        text_placed = False
        for i, part in enumerate(parts):
            if not text_placed and part.strip():
                result_parts.append(translated_text)
                text_placed = True
            elif text_placed:
                result_parts.append('')
            else:
                result_parts.append(part)

            if i < len(placeholders_in_order):
                result_parts.append(placeholders_in_order[i])

        if not text_placed:
            # 所有文本位置都是空的，放在开头
            result_parts.insert(0, translated_text)

        return ' '.join(p for p in result_parts if p)

    def _inject_to_paragraphs(self, structure: Dict, translated_text: str,
                              placeholder_map: Dict) -> str:
        """将翻译文本注入到段落结构中

        每个源段落保留其占位符，翻译文本按段落分配。
        """
        # 分割翻译文本为段落
        translated_paragraphs = [p.strip() for p in translated_text.split('\n\n')
                                if p.strip()]
        if not translated_paragraphs:
            translated_paragraphs = [p.strip() for p in translated_text.split('\n')
                                    if p.strip()]
        if not translated_paragraphs:
            translated_paragraphs = [translated_text.strip()]

        source_paragraphs = structure['paragraphs']
        result_paragraphs = []

        # 分配占位符到段落
        placeholder_assignments = self._assign_placeholders_to_paragraphs(
            source_paragraphs, placeholder_map
        )

        for i, source_para in enumerate(source_paragraphs):
            para_match = re.match(r'(<p[^>]*>)(.*?)(</p>)', source_para, re.DOTALL)
            if not para_match:
                result_paragraphs.append(source_para)
                continue

            opening_tag = para_match.group(1)
            para_content = para_match.group(2)
            closing_tag = para_match.group(3)

            # 获取对应的翻译段落
            if i < len(translated_paragraphs):
                trans_para = translated_paragraphs[i]
            else:
                trans_para = translated_paragraphs[-1] if translated_paragraphs else ''

            # 获取该段落的占位符
            para_placeholders = placeholder_assignments.get(i, [])

            if para_placeholders:
                # 将翻译文本和占位符按源段落中的位置组合
                rebuilt = self._rebuild_paragraph_with_placeholders(
                    para_content, trans_para, para_placeholders
                )
                result_paragraphs.append(f"{opening_tag}{rebuilt}{closing_tag}")
            else:
                result_paragraphs.append(f"{opening_tag}{trans_para}{closing_tag}")

        # 如果翻译段落比源段落多，添加额外段落
        if len(translated_paragraphs) > len(source_paragraphs):
            for extra_para in translated_paragraphs[len(source_paragraphs):]:
                result_paragraphs.append(f"<p>{extra_para}</p>")

        return '\n'.join(result_paragraphs)

    def _rebuild_paragraph_with_placeholders(self, source_para_content: str,
                                             translated_text: str,
                                             placeholders: List[str]) -> str:
        """重建段落内容，保留占位符在原始位置

        策略：用占位符分割源段落，将翻译文本填入非占位符位置。
        占位符保持在原始相对位置。
        """
        placeholder_pattern = re.compile(r'\[\[LINK_\d+\]\]')
        # 找出源段落中所有占位符的顺序
        found_placeholders = placeholder_pattern.findall(source_para_content)

        if not found_placeholders:
            return translated_text

        # 用占位符分割源段落，得到文本片段
        text_parts = placeholder_pattern.split(source_para_content)

        # 将翻译文本按比例分配到文本片段位置
        # 简单策略：将整个翻译文本放在第一个非空文本位置
        result_parts = []
        text_placed = False

        for i, part in enumerate(text_parts):
            stripped_part = re.sub(r'<[^>]+>', '', part).strip()
            if not text_placed and stripped_part:
                # 保留 part 中的 HTML 标签（如 <span>），替换文本
                html_tags_before = re.match(r'^(\s*(?:<[^>]+>\s*)*)', part)
                html_tags_after = re.search(r'((?:\s*<[^>]+>)*\s*)$', part)
                prefix = html_tags_before.group(1) if html_tags_before else ''
                suffix = html_tags_after.group(1) if html_tags_after else ''
                result_parts.append(f"{prefix}{translated_text}{suffix}")
                text_placed = True
            elif text_placed:
                # 保留 HTML 标签但清除文本
                html_only = re.sub(r'(?<=>)[^<]+(?=<)', '', part)
                html_only = re.sub(r'^[^<]+', '', html_only)
                html_only = re.sub(r'[^>]+$', '', html_only)
                result_parts.append(html_only if html_only.strip() else '')
            else:
                result_parts.append(part)

            if i < len(found_placeholders):
                result_parts.append(found_placeholders[i])

        if not text_placed:
            result_parts.insert(0, translated_text + ' ')

        return ''.join(result_parts)

    def _assign_placeholders_to_paragraphs(self, source_paragraphs: List[str],
                                           placeholder_map: Dict) -> Dict[int, List[str]]:
        """将占位符分配到对应的段落"""
        assignments: Dict[int, List[str]] = {}

        for placeholder in placeholder_map.keys():
            for i, para in enumerate(source_paragraphs):
                if placeholder in para:
                    if i not in assignments:
                        assignments[i] = []
                    assignments[i].append(placeholder)
                    break

        return assignments


# 便捷函数
def extract_for_translation(babele_json_path: str,
                            output_format: str = 'csv') -> str:
    """从 Babele JSON 提取纯文本的便捷函数"""
    converter = FormatConverter()
    return converter.extract_for_translation(babele_json_path, output_format)


# 向后兼容别名
def extract_for_weblate(babele_json_path: str,
                        output_format: str = 'csv') -> str:
    """向后兼容别名"""
    converter = FormatConverter()
    return converter.extract_for_translation(babele_json_path, output_format)


def inject_translations(source_json_path: str, translations_path: str,
                       output_path: Optional[str] = None) -> str:
    """注入翻译的便捷函数"""
    converter = FormatConverter()
    return converter.inject_translations(source_json_path, translations_path, output_path)
