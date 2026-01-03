#!/usr/bin/env python3
"""
Incremental Update CLI Entry Point

Usage:
    python -m automation.incremental_update update SOURCE_FILE EXISTING_TRANSLATION_FILE [--output OUTPUT_FILE]
    python -m automation.incremental_update batch SOURCE_DIR TRANSLATION_DIR [--pattern PATTERN]
    
Examples:
    # Update a single translation file
    python -m automation.incremental_update update en-US/swade-core-rules.swade-edges.json zh_Hans/swade-core-rules.swade-edges.json --output updated.json
    
    # Batch update all files in directories
    python -m automation.incremental_update batch en-US/ zh_Hans/ --pattern "*.json"
"""

import argparse
import json
import sys
from pathlib import Path

from .updater import IncrementalUpdater


def main():
    parser = argparse.ArgumentParser(
        description="Incrementally update translation files preserving existing translations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Update command
    update_parser = subparsers.add_parser(
        'update',
        help='Update a single translation file'
    )
    update_parser.add_argument(
        'source',
        help='Source JSON file (English)'
    )
    update_parser.add_argument(
        'translation',
        help='Existing translation JSON file'
    )
    update_parser.add_argument(
        '--output',
        help='Output file (default: overwrite translation file)'
    )
    update_parser.add_argument(
        '--backup',
        action='store_true',
        help='Create backup of original translation file'
    )
    
    # Batch command
    batch_parser = subparsers.add_parser(
        'batch',
        help='Batch update all files in directories'
    )
    batch_parser.add_argument(
        'source_dir',
        help='Source directory (English files)'
    )
    batch_parser.add_argument(
        'translation_dir',
        help='Translation directory'
    )
    batch_parser.add_argument(
        '--pattern',
        default='*.json',
        help='File pattern to match (default: *.json)'
    )
    batch_parser.add_argument(
        '--backup',
        action='store_true',
        help='Create backups of original translation files'
    )
    batch_parser.add_argument(
        '--report',
        help='Generate update report file'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == 'update':
            update_command(args)
        elif args.command == 'batch':
            batch_command(args)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def update_command(args):
    """Update a single translation file"""
    source_path = Path(args.source)
    translation_path = Path(args.translation)
    
    if not source_path.exists():
        print(f"Error: Source file '{args.source}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    if not translation_path.exists():
        print(f"Error: Translation file '{args.translation}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    updater = IncrementalUpdater()
    
    print(f"Updating translation: {args.source} -> {args.translation}", file=sys.stderr)
    
    # Create backup if requested
    if args.backup:
        backup_path = translation_path.with_suffix('.bak' + translation_path.suffix)
        backup_path.write_bytes(translation_path.read_bytes())
        print(f"✓ Backup created: {backup_path}", file=sys.stderr)
    
    # Perform incremental update
    result = updater.update_translation_file(args.source, args.translation)
    
    # Determine output path
    output_path = Path(args.output) if args.output else translation_path
    
    # Load and save updated translation
    with open(args.translation, 'r', encoding='utf-8') as f:
        updated_data = json.load(f)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(updated_data, f, ensure_ascii=False, indent=4)
    
    # Print summary
    print(f"✓ Update completed: {output_path}", file=sys.stderr)
    print(f"  Preserved: {len(result.preserved_entries)} entries", file=sys.stderr)
    print(f"  Added: {len(result.added_entries)} entries", file=sys.stderr)
    print(f"  Modified: {len(result.modified_entries)} entries", file=sys.stderr)
    print(f"  Merged: {len(result.merged_entries)} entries", file=sys.stderr)
    
    if result.conflicts:
        print(f"  Conflicts: {len(result.conflicts)} entries", file=sys.stderr)
        print("  Conflicted entries:", file=sys.stderr)
        for conflict in result.conflicts[:5]:  # Show first 5
            print(f"    - {conflict}", file=sys.stderr)
        if len(result.conflicts) > 5:
            print(f"    ... and {len(result.conflicts) - 5} more", file=sys.stderr)


def batch_command(args):
    """Batch update all files in directories"""
    source_dir = Path(args.source_dir)
    translation_dir = Path(args.translation_dir)
    
    if not source_dir.exists() or not source_dir.is_dir():
        print(f"Error: Source directory '{args.source_dir}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    if not translation_dir.exists() or not translation_dir.is_dir():
        print(f"Error: Translation directory '{args.translation_dir}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    updater = IncrementalUpdater()
    
    # Find all matching files
    source_files = list(source_dir.glob(args.pattern))
    all_results = []
    
    print(f"Batch updating {len(source_files)} files...", file=sys.stderr)
    
    for source_file in source_files:
        translation_file = translation_dir / source_file.name
        
        if not translation_file.exists():
            print(f"Warning: No translation file for {source_file.name}", file=sys.stderr)
            continue
        
        try:
            # Create backup if requested
            if args.backup:
                backup_path = translation_file.with_suffix('.bak' + translation_file.suffix)
                backup_path.write_bytes(translation_file.read_bytes())
            
            # Perform incremental update
            result = updater.update_translation_file(str(source_file), str(translation_file))
            all_results.append(result)
            
            # Print file summary
            changes = len(result.added_entries) + len(result.modified_entries) + len(result.merged_entries)
            conflicts = len(result.conflicts)
            
            status = "✓"
            if conflicts > 0:
                status = "⚠"
            
            print(f"  {status} {source_file.name}: {changes} changes, {conflicts} conflicts", file=sys.stderr)
            
        except Exception as e:
            print(f"Error updating {source_file.name}: {e}", file=sys.stderr)
    
    # Generate summary report
    if all_results:
        total_preserved = sum(len(r.preserved_entries) for r in all_results)
        total_added = sum(len(r.added_entries) for r in all_results)
        total_modified = sum(len(r.modified_entries) for r in all_results)
        total_merged = sum(len(r.merged_entries) for r in all_results)
        total_conflicts = sum(len(r.conflicts) for r in all_results)
        
        print(f"\nBatch Update Summary:", file=sys.stderr)
        print(f"  Files processed: {len(all_results)}", file=sys.stderr)
        print(f"  Preserved entries: {total_preserved}", file=sys.stderr)
        print(f"  Added entries: {total_added}", file=sys.stderr)
        print(f"  Modified entries: {total_modified}", file=sys.stderr)
        print(f"  Merged entries: {total_merged}", file=sys.stderr)
        print(f"  Conflicts: {total_conflicts}", file=sys.stderr)
        
        # Generate detailed report if requested
        if args.report:
            generate_batch_report(all_results, args.report)
            print(f"✓ Detailed report saved to '{args.report}'", file=sys.stderr)
        
        if total_conflicts > 0:
            print(f"\n⚠ {total_conflicts} conflicts require manual review", file=sys.stderr)
            sys.exit(1)
    else:
        print("No files were successfully processed", file=sys.stderr)
        sys.exit(1)


def generate_batch_report(results, report_path):
    """Generate a detailed batch update report"""
    lines = [
        "# Incremental Update Report",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Summary",
        f"- Files processed: {len(results)}",
        f"- Total preserved entries: {sum(len(r.preserved_entries) for r in results)}",
        f"- Total added entries: {sum(len(r.added_entries) for r in results)}",
        f"- Total modified entries: {sum(len(r.modified_entries) for r in results)}",
        f"- Total merged entries: {sum(len(r.merged_entries) for r in results)}",
        f"- Total conflicts: {sum(len(r.conflicts) for r in results)}",
        "",
        "## File Details",
        ""
    ]
    
    for result in results:
        if result.has_changes or result.conflicts:
            lines.append(f"### {result.file_name}")
            lines.append("")
            
            if result.added_entries:
                lines.append(f"**Added ({len(result.added_entries)}):**")
                for entry in result.added_entries[:10]:  # Show first 10
                    lines.append(f"- {entry}")
                if len(result.added_entries) > 10:
                    lines.append(f"- ... and {len(result.added_entries) - 10} more")
                lines.append("")
            
            if result.modified_entries:
                lines.append(f"**Modified ({len(result.modified_entries)}):**")
                for entry in result.modified_entries[:10]:
                    lines.append(f"- {entry}")
                if len(result.modified_entries) > 10:
                    lines.append(f"- ... and {len(result.modified_entries) - 10} more")
                lines.append("")
            
            if result.conflicts:
                lines.append(f"**Conflicts ({len(result.conflicts)}):**")
                for entry in result.conflicts:
                    lines.append(f"- {entry}")
                lines.append("")
    
    Path(report_path).write_text("\n".join(lines), encoding='utf-8')


if __name__ == "__main__":
    main()