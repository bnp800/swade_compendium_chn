#!/usr/bin/env python
"""翻译质量检查命令行工具

检查翻译文件的质量问题：占位符、HTML标签、UUID链接等。

Usage:
    python -m automation.cli.quality_check [options]
    python -m automation.cli.quality_check --help
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from automation.quality_checker import QualityChecker, Issue, QualityReport


def parse_args(args: List[str] = None) -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="检查翻译文件质量",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 检查默认目录
    python -m automation.cli.quality_check
    
    # 检查指定源和目标目录
    python -m automation.cli.quality_check --source en-US --target zh_Hans
    
    # 使用术语表检查
    python -m automation.cli.quality_check --glossary glossary/swade-glossary.json
    
    # 生成 Markdown 报告
    python -m automation.cli.quality_check --format markdown
"""
    )
    
    parser.add_argument(
        "--source", "-s",
        default="en-US",
        help="源文件目录 (默认: en-US)"
    )
    
    parser.add_argument(
        "--target", "-t",
        default="zh_Hans",
        help="目标文件目录 (默认: zh_Hans)"
    )
    
    parser.add_argument(
        "--glossary", "-g",
        type=str,
        help="术语表文件路径"
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
    
    parser.add_argument(
        "--error-only",
        action="store_true",
        help="只显示错误，忽略警告"
    )
    
    return parser.parse_args(args)


def load_glossary(glossary_path: str) -> Optional[Dict[str, str]]:
    """加载术语表
    
    Args:
        glossary_path: 术语表文件路径
        
    Returns:
        Dict[str, str]: 术语表 (英文 -> 中文)
    """
    if not glossary_path:
        return None
    
    path = Path(glossary_path)
    if not path.exists():
        print(f"警告: 术语表文件不存在: {glossary_path}", file=sys.stderr)
        return None
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 术语表格式: {"entries": {"English": "中文", ...}}
        if "entries" in data:
            return data["entries"]
        return data
    except Exception as e:
        print(f"警告: 加载术语表失败: {e}", file=sys.stderr)
        return None


def load_translation_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """加载翻译文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        Dict: 翻译数据
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"警告: 加载文件失败 {file_path}: {e}", file=sys.stderr)
        return None


def check_translation_pair(
    source_file: Path,
    target_file: Path,
    glossary: Optional[Dict[str, str]] = None
) -> List[Issue]:
    """检查一对翻译文件
    
    Args:
        source_file: 源文件路径
        target_file: 目标文件路径
        glossary: 术语表
        
    Returns:
        List[Issue]: 问题列表
    """
    issues = []
    checker = QualityChecker()
    
    source_data = load_translation_file(source_file)
    target_data = load_translation_file(target_file)
    
    if source_data is None or target_data is None:
        return issues
    
    source_entries = source_data.get("entries", {})
    target_entries = target_data.get("entries", {})
    
    # 检查每个条目
    for entry_name, source_entry in source_entries.items():
        target_entry = target_entries.get(entry_name, {})
        
        if not target_entry:
            continue  # 未翻译的条目跳过
        
        # 检查各个字段
        for field in ["name", "description", "category", "notes"]:
            source_value = source_entry.get(field, "")
            target_value = target_entry.get(field, "")
            
            if not source_value or not target_value:
                continue
            
            location = f"{source_file.name}:{entry_name}.{field}"
            
            # 执行所有检查
            field_issues = checker.check_all(
                source_value,
                target_value,
                glossary,
                location
            )
            issues.extend(field_issues)
    
    return issues


def generate_report(
    issues: List[Issue],
    format: str = "text",
    error_only: bool = False
) -> str:
    """生成质量报告
    
    Args:
        issues: 问题列表
        format: 报告格式
        error_only: 是否只显示错误
        
    Returns:
        str: 报告内容
    """
    if error_only:
        issues = [i for i in issues if i.severity == "error"]
    
    error_count = sum(1 for i in issues if i.severity == "error")
    warning_count = sum(1 for i in issues if i.severity == "warning")
    
    if format == "json":
        report = {
            "summary": {
                "total": len(issues),
                "errors": error_count,
                "warnings": warning_count
            },
            "issues": [
                {
                    "severity": i.severity,
                    "type": i.type,
                    "message": i.message,
                    "location": i.location
                }
                for i in issues
            ]
        }
        return json.dumps(report, ensure_ascii=False, indent=2)
    
    elif format == "markdown":
        lines = [
            "# 翻译质量检查报告",
            "",
            "## 摘要",
            "",
            f"- **总问题数**: {len(issues)}",
            f"- **错误**: {error_count}",
            f"- **警告**: {warning_count}",
            ""
        ]
        
        if issues:
            lines.append("## 问题详情")
            lines.append("")
            
            # 按位置分组
            by_location = {}
            for issue in issues:
                loc = issue.location
                if loc not in by_location:
                    by_location[loc] = []
                by_location[loc].append(issue)
            
            for location, loc_issues in sorted(by_location.items()):
                lines.append(f"### {location}")
                lines.append("")
                for issue in loc_issues:
                    severity_icon = "❌" if issue.severity == "error" else "⚠️"
                    lines.append(f"- {severity_icon} [{issue.type}] {issue.message}")
                lines.append("")
        
        return "\n".join(lines)
    
    else:  # text
        lines = [
            "翻译质量检查报告",
            "=" * 50,
            f"总问题数: {len(issues)}",
            f"错误: {error_count}",
            f"警告: {warning_count}",
            ""
        ]
        
        if issues:
            lines.append("问题详情:")
            lines.append("-" * 50)
            for issue in issues:
                severity = "ERROR" if issue.severity == "error" else "WARN"
                lines.append(f"[{severity}] {issue.location}: [{issue.type}] {issue.message}")
        
        return "\n".join(lines)


def main(args: List[str] = None) -> int:
    """主函数
    
    Args:
        args: 命令行参数列表
        
    Returns:
        int: 退出码 (0=成功, 1=有错误)
    """
    parsed = parse_args(args)
    
    source_dir = Path(parsed.source)
    target_dir = Path(parsed.target)
    
    if not source_dir.exists():
        print(f"错误: 源目录不存在: {parsed.source}", file=sys.stderr)
        return 1
    
    if not target_dir.exists():
        print(f"错误: 目标目录不存在: {parsed.target}", file=sys.stderr)
        return 1
    
    # 加载术语表
    glossary = load_glossary(parsed.glossary) if parsed.glossary else None
    
    all_issues = []
    
    # 查找所有源文件
    for source_file in sorted(source_dir.glob("*.json")):
        target_file = target_dir / source_file.name
        
        if not target_file.exists():
            if not parsed.quiet:
                print(f"跳过: {source_file.name} (目标文件不存在)", file=sys.stderr)
            continue
        
        issues = check_translation_pair(source_file, target_file, glossary)
        all_issues.extend(issues)
    
    # 生成报告
    report = generate_report(all_issues, parsed.format, parsed.error_only)
    
    # 输出报告
    if parsed.output:
        Path(parsed.output).write_text(report, encoding="utf-8")
        if not parsed.quiet:
            print(f"报告已保存到: {parsed.output}")
    else:
        if not parsed.quiet or all_issues:
            print(report)
    
    # 计算退出码
    error_count = sum(1 for i in all_issues if i.severity == "error")
    
    if parsed.strict and all_issues:
        return 1
    if error_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
