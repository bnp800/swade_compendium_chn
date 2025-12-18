#!/usr/bin/env python3
"""
从英文JSON中提取纯文本，用于翻译
功能：提取HTML中的文本内容，生成干净的文本映射
"""
import json
import re
import os
from html.parser import HTMLParser

class TextExtractor(HTMLParser):
    """HTML解析器，用于提取纯文本"""
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.ignore_tags = ['script', 'style']
        self.tag_stack = []

    def handle_starttag(self, tag, attrs):
        self.tag_stack.append(tag)

    def handle_endtag(self, tag):
        if self.tag_stack and self.tag_stack[-1] == tag:
            self.tag_stack.pop()

    def handle_data(self, data):
        # 忽略 script 和 style 标签内的内容
        if not any(tag in self.tag_stack for tag in self.ignore_tags):
            # 清理多余的空格和换行
            cleaned = data.strip()
            if cleaned:
                self.text_parts.append(cleaned)

    def get_text(self):
        # 合并文本，处理多余的换行
        return ' '.join(self.text_parts)

def extract_text_from_html(html_content):
    """从HTML中提取纯文本"""
    extractor = TextExtractor()
    extractor.feed(html_content)
    return extractor.get_text()

def extract_entries_from_file(json_file):
    """从JSON文件中提取所有条目的文本"""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    entries = data.get('entries', {})
    text_mapping = {}

    for key, value in entries.items():
        entry_data = {}

        # 提取 name 字段
        if 'name' in value:
            entry_data['name'] = value['name'].strip()

        # 提取 description 字段（HTML格式）
        if 'description' in value:
            desc_html = value['description']
            entry_data['description_html'] = desc_html
            entry_data['description_text'] = extract_text_from_html(desc_html)

        # 提取其他可能包含文本的字段
        for field in ['biography', 'text', 'notes']:
            if field in value:
                field_html = value[field]
                entry_data[f'{field}_html'] = field_html
                entry_data[f'{field}_text'] = extract_text_from_html(field_html)

        text_mapping[key] = entry_data

    return text_mapping

def save_as_json(data, output_file):
    """保存为JSON格式"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=False)
    print(f"✓ JSON文件已保存: {output_file}")

def save_as_csv(data, output_file):
    """保存为CSV格式，便于翻译"""
    import csv

    rows = []
    for key, entry_data in data.items():
        # 为每个字段创建一行
        if 'name' in entry_data:
            rows.append([key, 'name', entry_data['name'], ''])
        if 'description_text' in entry_data:
            rows.append([key, 'description', entry_data['description_text'], ''])
        if 'biography_text' in entry_data:
            rows.append([key, 'biography', entry_data['biography_text'], ''])

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['key', 'field', 'source_text', 'translated_text'])
        writer.writerows(rows)

    print(f"✓ CSV翻译模板已保存: {output_file}")

def main():
    import argparse

    parser = argparse.ArgumentParser(description='从英文JSON中提取文本内容用于翻译')
    parser.add_argument('input_json', help='输入的英文JSON文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径（默认：自动命名）')
    parser.add_argument('-f', '--format', choices=['json', 'csv'], default='csv',
                       help='输出格式：json（完整数据）或csv（翻译模板），默认csv')

    args = parser.parse_args()

    if not os.path.exists(args.input_json):
        print(f"错误：文件不存在: {args.input_json}")
        return

    print(f"正在提取文本: {args.input_json}")
    extracted_data = extract_entries_from_file(args.input_json)

    # 自动生成输出文件名
    if args.output:
        output_file = args.output
    else:
        base_name = os.path.splitext(os.path.basename(args.input_json))[0]
        output_file = f"{base_name}_extract.{args.format}"

    # 保存
    if args.format == 'json':
        save_as_json(extracted_data, output_file)
    else:
        save_as_csv(extracted_data, output_file)

    print(f"\n提取完成！共提取 {len(extracted_data)} 个条目")
    print(f"文件位置: {os.path.abspath(output_file)}")

if __name__ == '__main__':
    main()
