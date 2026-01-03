#!/usr/bin/env python3
"""
Quality Checker CLI Entry Point

Usage:
    python -m automation.quality_checker check SOURCE_FILE TRANSLATED_FILE [--glossary GLOSSARY_FILE]
    python -m automation.quality_checker batch SOURCE_DIR TRANSLATED_DIR [--glossary GLOSSARY_FILE]
    
Examples:
    # Check a single file
    python -m automation.quality_checker check en-US/swade-core-rules.swade-edges.json zh_Hans/swade-core-rules.swade-edges.json
    
    # Check all files in directories with glossary
    python -m automation.quality_checker batch en-US/ zh_Hans/ --glossary glossary/swade-glossary.json --format markdown --output quality-report.md
"""

import argparse
import json
import sys
from pathlib import Path

from .checker import QualityChecker
from .models import QualityReport


def main():
    parser = argparse.ArgumentParser(
        description="Check translation quality for consistency and errors",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Check command
    check_parser = subparsers.add_parser(
        'check',
        help='Check a single file pair'
    )
    check_parser.add_argument(
        'source',
        help='Source JSON file (English)'
    )
    check_parser.add_argument(
        'translated',
        help='Translated JSON file'
    )
    check_parser.add_argument(
        '--glossary',
        help='Glossary JSON file for terminology checking'
    )
    check_parser.add_argument(
        '--format',
        choices=['text', 'json', 'markdown'],
        default='text',
        help='Output format (default: text)'
    )
    check_parser.add_argument(
        '--output',
        help='Output file (default: stdout)'
    )
    
    # Batch command
    batch_parser = subparsers.add_parser(
        'batch',
        help='Check all files in directories'
    )
    batch_parser.add_argument(
        'source_dir',
        help='Source directory (English files)'
    )
    batch_parser.add_argument(
        'translated_dir',
        help='Translated directory'
    )
    batch_parser.add_argument(
        '--glossary',
        help='Glossary JSON file for terminology checking'
    )
    batch_parser.add_argument(
        '--format',
        choices=['text', 'json', 'markdown'],
        default='text',
        help='Output format (default: text)'
    )
    batch_parser.add_argument(
        '--output',
        help='Output file (default: stdout)'
    )
    batch_parser.add_argument(
        '--pattern',
        default='*.json',
        help='File pattern to match (default: *.json)'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == 'check':
            check_command(args)
        elif args.command == 'batch':
            batch_command(args)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def load_glossary(glossary_path: str) -> dict:
    """Load glossary from JSON file"""
    if not glossary_path:
        return {}
    
    path = Path(glossary_path)
    if not path.exists():
        print(f"Warning: Glossary file '{glossary_path}' not found", file=sys.stderr)
        return {}
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load glossary '{glossary_path}': {e}", file=sys.stderr)
        return {}


def check_file_pair(source_path: Path, translated_path: Path, glossary: dict) -> QualityReport:
    """Check a single file pair"""
    # Load source file
    with open(source_path, 'r', encoding='utf-8') as f:
        source_data = json.load(f)
    
    # Load translated file
    with open(translated_path, 'r', encoding='utf-8') as f:
        translated_data = json.load(f)
    
    checker = QualityChecker()
    all_issues = []
    
    # Check each entry
    source_entries = source_data.get('entries', {})
    translated_entries = translated_data.get('entries', {})
    
    for key, source_entry in source_entries.items():
        if key not in translated_entries:
            continue
        
        translated_entry = translated_entries[key]
        
        # Check each translatable field
        translatable_fields = ['name', 'description', 'text', 'notes', 'biography']
        
        for field in translatable_fields:
            if field in source_entry and field in translated_entry:
                source_text = source_entry[field]
                translated_text = translated_entry[field]
                
                if isinstance(source_text, str) and isinstance(translated_text, str):
                    location = f"{source_path.name}:{key}.{field}"
                    issues = checker.check_all(
                        source_text, 
                        translated_text, 
                        glossary, 
                        location
                    )
                    all_issues.extend(issues)
    
    return checker.generate_report(all_issues, str(source_path))


def check_command(args):
    """Check a single file pair"""
    source_path = Path(args.source)
    translated_path = Path(args.translated)
    
    if not source_path.exists():
        print(f"Error: Source file '{args.source}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    if not translated_path.exists():
        print(f"Error: Translated file '{args.translated}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    glossary = load_glossary(args.glossary)
    
    print(f"Checking quality: {args.source} -> {args.translated}", file=sys.stderr)
    
    report = check_file_pair(source_path, translated_path, glossary)
    
    # Generate output
    if args.format == 'json':
        output = report.to_json()
    elif args.format == 'markdown':
        output = report.to_markdown()
    else:
        # Text format
        lines = [f"Quality Check Report: {report.file_name}"]
        lines.append("=" * 50)
        lines.append(f"Total issues: {len(report.issues)}")
        lines.append(f"Errors: {report.error_count}")
        lines.append(f"Warnings: {report.warning_count}")
        lines.append(f"Info: {report.info_count}")
        lines.append("")
        
        if report.issues:
            lines.append("Issues:")
            lines.append("-" * 30)
            for issue in report.issues:
                lines.append(str(issue))
        else:
            lines.append("✓ No issues found!")
        
        output = "\n".join(lines)
    
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding='utf-8')
        print(f"✓ Report saved to '{args.output}'", file=sys.stderr)
    else:
        print(output)
    
    # Exit with error code if issues found
    if report.has_errors:
        sys.exit(1)


def batch_command(args):
    """Check all files in directories"""
    source_dir = Path(args.source_dir)
    translated_dir = Path(args.translated_dir)
    
    if not source_dir.exists() or not source_dir.is_dir():
        print(f"Error: Source directory '{args.source_dir}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    if not translated_dir.exists() or not translated_dir.is_dir():
        print(f"Error: Translated directory '{args.translated_dir}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    glossary = load_glossary(args.glossary)
    
    # Find all matching files
    source_files = list(source_dir.glob(args.pattern))
    all_reports = []
    
    print(f"Checking {len(source_files)} files...", file=sys.stderr)
    
    for source_file in source_files:
        translated_file = translated_dir / source_file.name
        
        if not translated_file.exists():
            print(f"Warning: No translated file for {source_file.name}", file=sys.stderr)
            continue
        
        try:
            report = check_file_pair(source_file, translated_file, glossary)
            all_reports.append(report)
            
            issue_count = len(report.issues)
            error_count = len([i for i in report.issues if i.severity == 'error'])
            print(f"  {source_file.name}: {issue_count} issues ({error_count} errors)", file=sys.stderr)
            
        except Exception as e:
            print(f"Error checking {source_file.name}: {e}", file=sys.stderr)
    
    # Generate combined report
    if all_reports:
        combined_report = QualityReport.combine_reports(all_reports)
        
        if args.format == 'json':
            output = combined_report.to_json()
        elif args.format == 'markdown':
            output = combined_report.to_markdown()
        else:
            # Text format
            lines = [f"Combined Quality Check Report ({len(all_reports)} files)"]
            lines.append("=" * 60)
            lines.append(f"Total issues: {len(combined_report.issues)}")
            lines.append(f"Errors: {combined_report.error_count}")
            lines.append(f"Warnings: {combined_report.warning_count}")
            lines.append(f"Info: {combined_report.info_count}")
            lines.append("")
            
            if combined_report.issues:
                lines.append("Issues by file:")
                lines.append("-" * 40)
                by_location = combined_report.issues_by_location()
                for location, issues in sorted(by_location.items()):
                    file_part = location.split(':')[0]
                    lines.append(f"\n{file_part}:")
                    for issue in issues:
                        lines.append(f"  {issue}")
            else:
                lines.append("✓ No issues found in any file!")
            
            output = "\n".join(lines)
        
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output, encoding='utf-8')
            print(f"✓ Combined report saved to '{args.output}'", file=sys.stderr)
        else:
            print(output)
        
        # Summary
        total_issues = sum(len(r.issues) for r in all_reports)
        total_errors = sum(len([i for i in r.issues if i.severity == 'error']) for r in all_reports)
        
        print(f"\nSummary: {len(all_reports)} files checked, {total_issues} issues ({total_errors} errors)", file=sys.stderr)
        
        if total_errors > 0:
            sys.exit(1)
    else:
        print("No files were successfully checked", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()