#!/usr/bin/env python3
"""
Change Detector CLI Entry Point

Usage:
    python -m automation.change_detector.detector SOURCE_DIR [--output OUTPUT_FILE] [--target TARGET_DIR]
    
Examples:
    # Generate changelog comparing en-US to current state
    python -m automation.change_detector.detector en-US/ --output changelog.md
    
    # Compare en-US to zh_Hans and generate changelog
    python -m automation.change_detector.detector en-US/ --target zh_Hans/ --output changelog.md
"""

import argparse
import sys
from pathlib import Path

from .detector import ChangeDetector


def main():
    parser = argparse.ArgumentParser(
        description="Detect changes in SWADE translation files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "source_dir",
        help="Source directory containing JSON files (e.g., en-US/)"
    )
    
    parser.add_argument(
        "--target",
        dest="target_dir",
        help="Target directory to compare against (optional)"
    )
    
    parser.add_argument(
        "--output",
        dest="output_file",
        default="changelog.md",
        help="Output file for changelog (default: changelog.md)"
    )
    
    parser.add_argument(
        "--sync-placeholders",
        action="store_true",
        help="Create placeholder files in target directory for missing files"
    )
    
    args = parser.parse_args()
    
    # Validate source directory
    source_path = Path(args.source_dir)
    if not source_path.exists():
        print(f"Error: Source directory '{args.source_dir}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    if not source_path.is_dir():
        print(f"Error: '{args.source_dir}' is not a directory", file=sys.stderr)
        sys.exit(1)
    
    # Initialize detector
    detector = ChangeDetector()
    
    try:
        # Sync placeholder files if requested
        if args.sync_placeholders and args.target_dir:
            created_files = detector.sync_placeholder_files(args.source_dir, args.target_dir)
            if created_files:
                print(f"Created {len(created_files)} placeholder files:")
                for file_path in created_files:
                    print(f"  - {file_path}")
                print()
        
        # Detect changes
        print(f"Detecting changes in '{args.source_dir}'...")
        if args.target_dir:
            print(f"Comparing against '{args.target_dir}'...")
        
        changes = detector.detect_changes(args.source_dir, args.target_dir)
        
        # Generate changelog
        changelog = detector.generate_changelog(changes)
        
        # Write output
        output_path = Path(args.output_file)
        output_path.write_text(changelog, encoding='utf-8')
        
        # Print summary
        total_files = len(changes)
        files_with_changes = len([c for c in changes if c.has_changes])
        total_added = sum(len(c.added_entries) for c in changes)
        total_modified = sum(len(c.modified_entries) for c in changes)
        total_deleted = sum(len(c.deleted_entries) for c in changes)
        
        print(f"✓ Changelog generated: {args.output_file}")
        print(f"  Files processed: {total_files}")
        print(f"  Files with changes: {files_with_changes}")
        print(f"  Added entries: {total_added}")
        print(f"  Modified entries: {total_modified}")
        print(f"  Deleted entries: {total_deleted}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()