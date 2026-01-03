#!/usr/bin/env python
"""JSON 验证命令行工具

验证翻译文件的 JSON 语法正确性。

Usage:
    python -m automation.cli.validate [directories...]
    python -m automation.cli.validate --help
"""

import argparse
import sys
from pathlib import Path
from typing import List

from automation.json_validator import JSONValidator


def parse_args(args: List[str] = None) -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="验证 JSON 文件语法正确性",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 验证默认目录
    python -m automation.cli.validate
    
    # 验证指定目录
    python -m automation.cli.validate en-US zh_Hans
    
    # 生成 Markdown 报告
    python -m automation.cli.validate --format markdown
"""
    )
    
    parser.add_argument(
        "directories",
        nargs="*",
        default=["en-US", "zh_Hans", "glossary", "mappings"],
        help="要验证的目录列表 (默认: en-US zh_Hans glossary mappings)"
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["text", "markdown", "json"],
        default="text",
        help="输出格式 (默认: text)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出文件路径 (默认: 标准输出)"
    )
    
    parser.add_argument(
        "--strict",
        action="store_true",
        help="严格模式：任何错误都返回非零退出码"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="安静模式：只输出错误"
    )
    
    return parser.parse_args(args)


def main(args: List[str] = None) -> int:
    """主函数
    
    Args:
        args: 命令行参数列表
        
    Returns:
        int: 退出码 (0=成功, 1=有错误)
    """
    parsed = parse_args(args)
    
    validator = JSONValidator()
    all_results = []
    
    # 验证每个目录
    for directory in parsed.directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            if not parsed.quiet:
                print(f"警告: 目录不存在: {directory}", file=sys.stderr)
            continue
        
        results = validator.validate_directory(dir_path, recursive=False)
        all_results.extend(results)
    
    # 生成报告
    report = validator.generate_report(all_results, format=parsed.format)
    
    # 输出报告
    if parsed.output:
        Path(parsed.output).write_text(report, encoding="utf-8")
        if not parsed.quiet:
            print(f"报告已保存到: {parsed.output}")
    else:
        if not parsed.quiet or any(not r.is_valid for r in all_results):
            print(report)
    
    # 计算退出码
    has_errors = any(not r.is_valid for r in all_results)
    
    if has_errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
