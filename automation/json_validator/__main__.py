#!/usr/bin/env python3
"""
JSON Validator CLI Entry Point

Usage:
    python -m automation.json_validator FILE_OR_DIR [--format FORMAT] [--output OUTPUT_FILE]
    
Examples:
    # Validate a single file
    python -m automation.json_validator en-US/swade-core-rules.swade-edges.json
    
    # Validate all JSON files in a directory
    python -m automation.json_validator zh_Hans/ --format markdown --output validation-report.md
    
    # Validate multiple directories
    python -m automation.json_validator en-US/ zh_Hans/ --format json --output validation.json
"""

import argparse
import sys
from pathlib import Path

from .validator import JSONValidator


def main():
    parser = argparse.ArgumentParser(
        description="Validate JSON files for syntax errors",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        'paths',
        nargs='+',
        help='JSON files or directories to validate'
    )
    
    parser.add_argument(
        '--format',
        choices=['text', 'markdown', 'json'],
        default='text',
        help='Report format (default: text)'
    )
    
    parser.add_argument(
        '--output',
        help='Output file for report (default: stdout)'
    )
    
    parser.add_argument(
        '--pattern',
        default='*.json',
        help='File pattern for directory validation (default: *.json)'
    )
    
    parser.add_argument(
        '--no-recursive',
        action='store_true',
        help='Do not search subdirectories recursively'
    )
    
    args = parser.parse_args()
    
    validator = JSONValidator()
    all_results = []
    
    try:
        for path_str in args.paths:
            path = Path(path_str)
            
            if not path.exists():
                print(f"Error: Path '{path_str}' does not exist", file=sys.stderr)
                sys.exit(1)
            
            if path.is_file():
                # Validate single file
                result = validator.validate_file(path)
                all_results.append(result)
                print(f"Validating file: {path_str}", file=sys.stderr)
            elif path.is_dir():
                # Validate directory
                print(f"Validating directory: {path_str}", file=sys.stderr)
                results = validator.validate_directory(
                    path, 
                    pattern=args.pattern,
                    recursive=not args.no_recursive
                )
                all_results.extend(results)
            else:
                print(f"Error: '{path_str}' is neither a file nor directory", file=sys.stderr)
                sys.exit(1)
        
        # Generate report
        report = validator.generate_report(all_results, args.format)
        
        # Output report
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report, encoding='utf-8')
            print(f"✓ Report saved to '{args.output}'", file=sys.stderr)
        else:
            print(report)
        
        # Exit with error code if any files are invalid
        invalid_count = sum(1 for r in all_results if not r.is_valid)
        if invalid_count > 0:
            print(f"✗ {invalid_count} file(s) failed validation", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"✓ All {len(all_results)} file(s) are valid", file=sys.stderr)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()