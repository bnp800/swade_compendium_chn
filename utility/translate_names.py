#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os

def load_json_file(file_path):
    """加载JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json_file(file_path, data):
    """保存JSON文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def translate_names(obj, translation_map):
    """递归遍历对象，替换name字段的值"""
    if isinstance(obj, dict):
        # 如果是字典，检查是否有name字段
        if 'name' in obj and isinstance(obj['name'], str):
            # 如果name字段的值在映射关系中存在，则替换
            if obj['name'] in translation_map:
                obj['name'] = translation_map[obj['name']]
        
        # 递归处理字典中的所有值
        for key, value in obj.items():
            translate_names(value, translation_map)
    
    elif isinstance(obj, list):
        # 如果是列表，递归处理列表中的所有元素
        for item in obj:
            translate_names(item, translation_map)

def main():
    # 文件路径
    glossary_path = 'glossary/swpf-glossary.json'
    target_path = 'zh_Hans/swpf-core-rules.swpf-rules.json'
    
    # 加载文件
    translation_map = load_json_file(glossary_path)
    target_data = load_json_file(target_path)
    
    # 替换name字段的值
    translate_names(target_data, translation_map)
    
    # 保存修改后的文件
    save_json_file(target_path, target_data)
    
    print(f"翻译完成，已保存到 {target_path}")

if __name__ == "__main__":
    main() 