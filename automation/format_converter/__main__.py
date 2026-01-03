#!/usr/bin/env python3
"""
Format Converter CLI Entry Point

Usage:
    python -m automation.format_converter extract INPUT_FILE [--output OUTPUT_FILE] [--format FORMAT]
    python -m automation.format_converter inject SOURCE_FILE TRANSLATIONS_FILE [--output OUTPUT_FILE]
    
Examples:
    # Extract to PO format for Weblate
    python -m automation.format_converter extract en-US/swade-core-rules.swade-armors.json --output weblate/armor.po --format po
    
    # Extract to CSV format
    python -m automation.format_converter extract en-US/swade-core-rules.swade-edges.json --output translations/edges.csv --format csv
    
    # Inject translations back to JSON
    python -m automation.format_converter inject en-US/source.json translations/armor.po --output zh_Hans/armor.json
"""

import argparse
import sys
from pathlib import Path

from .converter import FormatConverter


def main():
    parser = argparse.ArgumentParser(
        description="Convert between Babele JSON and translation formats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Extract command
    extract_parser = subparsers.add_parser(
        'extract', 
        help='Extract translatable text from Babele JSON'
    )
    extract_parser.add_argument(
        'input',
        help='Input Babele JSON file'
    )
    extract_parser.add_argument(
        '--output',
        help='Output file (default: stdout)'
    )
    extract_parser.add_argument(
        '--format',
        choices=['po', 'csv', 'json'],
        default='po',
        help='Output format (default: po)'
    )
    
    # Inject command
    inject_parser = subparsers.add_parser(
        'inject',
        help='Inject translations back into Babele JSON'
    )
    inject_parser.add_argument(
        'source',
        help='Source Babele JSON file'
    )
    inject_parser.add_argument(
        'translations',
        help='Translation file (PO, CSV, or JSON)'
    )
    inject_parser.add_argument(
        '--output',
        help='Output JSON file (default: stdout)'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    converter = FormatConverter()
    
    try:
        if args.command == 'extract':
            # Validate input file
            input_path = Path(args.input)
            if not input_path.exists():
                print(f"Error: Input file '{args.input}' does not exist", file=sys.stderr)
                sys.exit(1)
            
            print(f"Extracting from '{args.input}' in {args.format} format...", file=sys.stderr)
            
            # Extract content
            result = converter.extract_for_weblate(args.input, args.format)
            
            # Output result
            if args.output:
                output_path = Path(args.output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(result, encoding='utf-8')
                print(f"✓ Extracted to '{args.output}'", file=sys.stderr)
            else:
                print(result)
                
        elif args.command == 'inject':
            # Validate input files
            source_path = Path(args.source)
            if not source_path.exists():
                print(f"Error: Source file '{args.source}' does not exist", file=sys.stderr)
                sys.exit(1)
                
            trans_path = Path(args.translations)
            if not trans_path.exists():
                print(f"Error: Translation file '{args.translations}' does not exist", file=sys.stderr)
                sys.exit(1)
            
            print(f"Injecting translations from '{args.translations}' into '{args.source}'...", file=sys.stderr)
            
            # Inject translations
            result = converter.inject_translations(args.source, args.translations)
            
            # Output result
            if args.output:
                output_path = Path(args.output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(result, encoding='utf-8')
                print(f"✓ Injected translations to '{args.output}'", file=sys.stderr)
            else:
                print(result)
                
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()