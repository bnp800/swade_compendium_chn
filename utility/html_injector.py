#!/usr/bin/env python3
"""
HTML注入器 - 将纯文本翻译嵌入到英文HTML结构中
核心功能：保持HTML标签、类名、UUID链接不变，只替换文本内容
"""
import json
import re
import csv
import os
import html
from html.parser import HTMLParser
from collections import defaultdict

class HTMLInjector:
    """
    智能HTML注入器
    从英文HTML中提取结构，注入中文文本
    """

    def __init__(self):
        self.translation_map = {}
        self.link_patterns = {
            'uuid': r'@UUID\[([^\]]+)\]\{([^}]+)\}',
            'compendium': r'@Compendium\[([^\]]+)\]\{([^}]+)\}',
            'compendium_plain': r'@Compendium\[([^\]]+)\]',
            'uuid_plain': r'@UUID\[([^\]]+)\]'
        }

    def load_translation_csv(self, csv_file):
        """从CSV文件加载翻译"""
        translation_dict = defaultdict(dict)

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row.get('key', '').strip()
                field = row.get('field', '').strip()
                translated = row.get('translated_text', '').strip()

                if key and field and translated:
                    translation_dict[key][field] = translated

        self.translation_map = dict(translation_dict)
        print(f"✓ 已加载 {len(self.translation_map)} 个条目的翻译")
        return self.translation_map

    def load_translation_json(self, json_file):
        """从JSON文件加载翻译"""
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.translation_map = data
        print(f"✓ 已加载 {len(self.translation_map)} 个条目的翻译")
        return self.translation_map

    def extract_link_placeholders(self, html_content):
        """
        提取HTML中的链接标记，替换为占位符
        返回：(处理后的文本, 占位符映射)
        """
        placeholder_map = {}
        placeholder_id = 0
        processed = html_content

        # 提取 UUID 链接: @UUID[...]{text}
        for match in re.finditer(self.link_patterns['uuid'], processed):
            full_match = match.group(0)
            uuid_ref = match.group(1)
            link_text = match.group(2)
            placeholder = f"__LINK_PLACEHOLDER_{placeholder_id}__"
            placeholder_map[placeholder] = {
                'type': 'uuid',
                'full': full_match,
                'ref': uuid_ref,
                'text': link_text
            }
            processed = processed.replace(full_match, placeholder)
            placeholder_id += 1

        # 提取 Compendium 链接: @Compendium[...]{text}
        for match in re.finditer(self.link_patterns['compendium'], processed):
            full_match = match.group(0)
            comp_ref = match.group(1)
            link_text = match.group(2)
            placeholder = f"__LINK_PLACEHOLDER_{placeholder_id}__"
            placeholder_map[placeholder] = {
                'type': 'compendium',
                'full': full_match,
                'ref': comp_ref,
                'text': link_text
            }
            processed = processed.replace(full_match, placeholder)
            placeholder_id += 1

        # 提取纯链接: @Compendium[...] 或 @UUID[...]
        for pattern_name in ['compendium_plain', 'uuid_plain']:
            for match in re.finditer(self.link_patterns[pattern_name], processed):
                full_match = match.group(0)
                ref = match.group(1)
                placeholder = f"__LINK_PLACEHOLDER_{placeholder_id}__"
                placeholder_map[placeholder] = {
                    'type': pattern_name.replace('_plain', ''),
                    'full': full_match,
                    'ref': ref,
                    'text': ''
                }
                processed = processed.replace(full_match, placeholder)
                placeholder_id += 1

        return processed, placeholder_map

    def restore_links(self, content, placeholder_map):
        """恢复链接标记"""
        restored = content
        for placeholder, link_data in placeholder_map.items():
            restored = restored.replace(placeholder, link_data['full'])
        return restored

    def align_translation(self, source_html, translated_text):
        """
        核心对齐算法：将纯文本翻译嵌入到HTML结构中
        策略：保持HTML框架，按段落结构对齐
        """
        if not translated_text.strip():
            return source_html

        # 1. 提取链接并替换为占位符
        source_processed, placeholder_map = self.extract_link_placeholders(source_html)

        # 2. 按段落分割
        # 使用 </p> 作为段落分隔符
        paragraphs = re.split(r'(</p>)', source_processed)

        # 3. 清理段落，提取文本
        source_paragraphs = []
        for i in range(0, len(paragraphs) - 1, 2):
            text = paragraphs[i]
            if text.strip():
                # 移除HTML标签
                clean_text = re.sub(r'<[^>]+>', '', text)
                # 清理多余空格
                clean_text = ' '.join(clean_text.split())
                source_paragraphs.append(clean_text)

        # 4. 将翻译文本也按段落分割
        translated_paragraphs = []
        # 按换行或句号分割
        temp_paras = re.split(r'\n+', translated_text.strip())
        for para in temp_paras:
            if para.strip():
                # 进一步处理长段落
                sentences = re.split(r'(。！？)', para.strip())
                current = ''
                for i in range(0, len(sentences), 2):
                    sentence = sentences[i]
                    if i + 1 < len(sentences):
                        sentence += sentences[i + 1]
                    current += sentence
                    if len(current) > 30:  # 段落较短时开始新段落
                        translated_paragraphs.append(current.strip())
                        current = ''
                if current.strip():
                    translated_paragraphs.append(current.strip())

        # 5. 对齐并替换
        result_paragraphs = []

        # 确保段落数量一致
        max_len = max(len(source_paragraphs), len(translated_paragraphs))
        for i in range(max_len):
            if i < len(paragraphs):
                para_html = paragraphs[i * 2]

                # 找到对应的翻译
                if i < len(translated_paragraphs):
                    translated_para = translated_paragraphs[i]

                    # 提取当前段落中的所有链接占位符
                    links_in_para = {}
                    for ph, link in placeholder_map.items():
                        if ph in para_html:
                            links_in_para[ph] = link

                    # 恢复链接
                    para_with_links = translated_para
                    for ph in links_in_para.keys():
                        if ph in para_html:
                            para_with_links = para_with_links + ' ' + ph

                    # 替换HTML中的文本内容
                    # 保留标签，只替换文本
                    def replace_text_in_para(html_content, new_text):
                        # 提取所有标签
                        tags = re.findall(r'(<[^>]+>)', html_content)
                        if not tags:
                            return new_text

                        # 重建HTML
                        result = html_content
                        # 移除所有占位符
                        for ph in placeholder_map.keys():
                            result = result.replace(ph, '')
                        # 移除文本内容
                        result = re.sub(r'>([^<]+)<', '><', result)

                        # 插入新文本
                        # 找到第一个闭合标签后插入
                        first_close = result.find('>') + 1
                        if first_close > 0:
                            result = result[:first_close] + new_text + result[first_close:]

                        # 恢复占位符
                        for ph, link in placeholder_map.items():
                            if ph in para_html:
                                result = result.replace(ph, link['full'])

                        return result

                    # 替换文本
                    if para_html.strip():
                        new_para = replace_text_in_para(para_html, para_with_links)
                        result_paragraphs.append(new_para)
                        if i * 2 + 1 < len(paragraphs):
                            result_paragraphs.append(paragraphs[i * 2 + 1])  # 添加</p>
                    else:
                        result_paragraphs.append(para_html)
                        if i * 2 + 1 < len(paragraphs):
                            result_paragraphs.append(paragraphs[i * 2 + 1])
                else:
                    result_paragraphs.append(para_html)
                    if i * 2 + 1 < len(paragraphs):
                        result_paragraphs.append(paragraphs[i * 2 + 1])

        # 6. 恢复链接
        result = ''.join(result_paragraphs)
        result = self.restore_links(result, placeholder_map)

        return result

    def process_json_file(self, source_json, translation_file, output_file=None):
        """
        处理完整的JSON文件
        """
        # 加载源数据（英文JSON）
        with open(source_json, 'r', encoding='utf-8') as f:
            source_data = json.load(f)

        # 加载翻译
        if translation_file.endswith('.csv'):
            self.load_translation_csv(translation_file)
        else:
            self.load_translation_json(translation_file)

        # 处理条目
        entries = source_data.get('entries', {})
        processed_count = 0
        missing_count = 0

        for key, entry_value in entries.items():
            if key in self.translation_map:
                translated_entry = self.translation_map[key]

                # 处理 name 字段
                if 'name' in entry_value and 'name' in translated_entry:
                    entry_value['name'] = translated_entry['name']

                # 处理 description 字段（核心部分）
                if 'description' in entry_value and 'description' in translated_entry:
                    translated_desc = translated_entry['description']
                    source_desc = entry_value['description']

                    # 如果翻译已经是HTML格式，直接替换
                    if '<' in translated_desc and '>' in translated_desc:
                        entry_value['description'] = translated_desc
                    else:
                        # 否则将文本注入到HTML结构中
                        entry_value['description'] = self.align_translation(
                            source_desc, translated_desc
                        )

                # 处理其他字段
                for field in ['biography', 'text', 'notes']:
                    field_html_key = field
                    field_text_key = field

                    if field_html_key in entry_value and field_text_key in translated_entry:
                        translated_text = translated_entry[field_text_key]
                        source_html = entry_value[field_html_key]

                        # 检查是否包含HTML
                        if '<' in translated_text and '>' in translated_text:
                            entry_value[field_html_key] = translated_text
                        else:
                            entry_value[field_html_key] = self.align_translation(
                                source_html, translated_text
                            )

                processed_count += 1
            else:
                missing_count += 1
                print(f"⚠ 未找到 '{key}' 的翻译")

        # 保存结果
        if not output_file:
            base_name = os.path.splitext(os.path.basename(source_json))[0]
            output_file = f"{base_name}_translated.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(source_data, f, indent=4, ensure_ascii=False, sort_keys=False)

        print(f"\n✓ 处理完成！")
        print(f"  已处理: {processed_count} 个条目")
        print(f"  未找到翻译: {missing_count} 个条目")
        print(f"  输出文件: {os.path.abspath(output_file)}")

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='将纯文本翻译嵌入到英文JSON的HTML结构中',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 从CSV翻译文件注入
  python html_injector.py en-US/swade-rules.json translations.csv -o zh_Hans/swade-rules.json

  # 从JSON翻译文件注入
  python html_injector.py en-US/swade-rules.json translations.json
        """
    )

    parser.add_argument('source_json', help='源英文JSON文件路径（包含HTML结构）')
    parser.add_argument('translation_file', help='翻译文件路径（CSV或JSON格式）')
    parser.add_argument('-o', '--output', help='输出文件路径（可选）')

    args = parser.parse_args()

    if not os.path.exists(args.source_json):
        print(f"错误：源文件不存在: {args.source_json}")
        return

    if not os.path.exists(args.translation_file):
        print(f"错误：翻译文件不存在: {args.translation_file}")
        return

    injector = HTMLInjector()
    injector.process_json_file(args.source_json, args.translation_file, args.output)

if __name__ == '__main__':
    main()
