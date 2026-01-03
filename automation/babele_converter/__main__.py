#!/usr/bin/env python3
"""
Babele Converter CLI Entry Point

Usage:
    python -m automation.babele_converter validate SOURCE_FILE TRANSLATED_FILE
    python -m automation.babele_converter test-reuse PACK_DIR
    
Examples:
    # Validate translation completeness
    python -m automation.babele_converter validate en-US/swade-core-rules.swade-edges.json zh_Hans/swade-core-rules.swade-edges.json
    
    # Test embedded item reuse functionality
    python -m automation.babele_converter test-reuse zh_Hans/
"""

import argparse
import json
import sys
from pathlib import Path

from .converter import (
    validate_translation_completeness,
    translate_embedded_items,
    find_translation_from_packs,
    get_all_translatable_fields
)


def main():
    parser = argparse.ArgumentParser(
        description="Babele converter testing and validation tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Validate command
    validate_parser = subparsers.add_parser(
        'validate',
        help='Validate translation completeness'
    )
    validate_parser.add_argument(
        'source',
        help='Source JSON file (English)'
    )
    validate_parser.add_argument(
        'translated',
        help='Translated JSON file'
    )
    validate_parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )
    
    # Test reuse command
    reuse_parser = subparsers.add_parser(
        'test-reuse',
        help='Test embedded item reuse functionality'
    )
    reuse_parser.add_argument(
        'pack_dir',
        help='Directory containing translation packs'
    )
    reuse_parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed reuse information'
    )
    
    # Fields command
    fields_parser = subparsers.add_parser(
        'fields',
        help='List all translatable fields in a file'
    )
    fields_parser.add_argument(
        'file',
        help='JSON file to analyze'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == 'validate':
            validate_command(args)
        elif args.command == 'test-reuse':
            test_reuse_command(args)
        elif args.command == 'fields':
            fields_command(args)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def validate_command(args):
    """Validate translation completeness"""
    source_path = Path(args.source)
    translated_path = Path(args.translated)
    
    if not source_path.exists():
        print(f"Error: Source file '{args.source}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    if not translated_path.exists():
        print(f"Error: Translated file '{args.translated}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    # Load files
    with open(source_path, 'r', encoding='utf-8') as f:
        source_data = json.load(f)
    
    with open(translated_path, 'r', encoding='utf-8') as f:
        translated_data = json.load(f)
    
    # Validate each entry
    source_entries = source_data.get('entries', {})
    translated_entries = translated_data.get('entries', {})
    
    all_results = []
    
    for key, source_entry in source_entries.items():
        if key in translated_entries:
            result = validate_translation_completeness(source_entry, translated_entries[key])
            result['entry_key'] = key
            all_results.append(result)
        else:
            all_results.append({
                'entry_key': key,
                'complete': False,
                'missing': ['entire_entry'],
                'total_fields': len(get_all_translatable_fields(source_entry)),
                'translated_fields': 0
            })
    
    # Generate output
    if args.format == 'json':
        output = {
            'summary': {
                'total_entries': len(source_entries),
                'translated_entries': len([r for r in all_results if r['complete']]),
                'total_fields': sum(r['total_fields'] for r in all_results),
                'translated_fields': sum(r['translated_fields'] for r in all_results)
            },
            'results': all_results
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        # Text format
        total_entries = len(source_entries)
        complete_entries = len([r for r in all_results if r['complete']])
        total_fields = sum(r['total_fields'] for r in all_results)
        translated_fields = sum(r['translated_fields'] for r in all_results)
        
        print(f"Translation Validation Report")
        print(f"=" * 50)
        print(f"Entries: {complete_entries}/{total_entries} complete ({complete_entries/total_entries*100:.1f}%)")
        print(f"Fields: {translated_fields}/{total_fields} translated ({translated_fields/total_fields*100:.1f}%)")
        print()
        
        incomplete = [r for r in all_results if not r['complete']]
        if incomplete:
            print("Incomplete entries:")
            print("-" * 30)
            for result in incomplete[:10]:  # Show first 10
                missing_count = len(result['missing'])
                print(f"  {result['entry_key']}: {missing_count} missing fields")
                if missing_count < 5:  # Show details for entries with few missing fields
                    for field in result['missing']:
                        print(f"    - {field}")
            
            if len(incomplete) > 10:
                print(f"  ... and {len(incomplete) - 10} more entries")


def test_reuse_command(args):
    """Test embedded item reuse functionality"""
    pack_dir = Path(args.pack_dir)
    
    if not pack_dir.exists() or not pack_dir.is_dir():
        print(f"Error: Directory '{args.pack_dir}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    # Load all JSON files as packs
    packs = []
    for json_file in pack_dir.glob('*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                packs.append({
                    'name': json_file.stem,
                    'path': str(json_file),
                    'translated': True,
                    'translations': data.get('entries', {})
                })
        except Exception as e:
            print(f"Warning: Could not load {json_file}: {e}", file=sys.stderr)
    
    print(f"Loaded {len(packs)} translation packs")
    
    # Test reuse functionality
    reuse_stats = {}
    
    for pack in packs:
        pack_name = pack['name']
        translations = pack['translations']
        
        for entry_name, entry_data in translations.items():
            # Look for embedded items
            items = entry_data.get('items', [])
            if items:
                translated_items = translate_embedded_items(
                    items, {}, packs, pack
                )
                
                reused_count = sum(
                    1 for item in translated_items 
                    if item.get('_translationSource') == 'compendium-reuse'
                )
                
                if reused_count > 0:
                    if pack_name not in reuse_stats:
                        reuse_stats[pack_name] = []
                    reuse_stats[pack_name].append({
                        'entry': entry_name,
                        'total_items': len(items),
                        'reused_items': reused_count
                    })
    
    # Report results
    if reuse_stats:
        print("\nEmbedded Item Reuse Results:")
        print("-" * 40)
        for pack_name, entries in reuse_stats.items():
            total_reused = sum(e['reused_items'] for e in entries)
            print(f"{pack_name}: {total_reused} items reused across {len(entries)} entries")
            
            if args.verbose:
                for entry in entries:
                    print(f"  {entry['entry']}: {entry['reused_items']}/{entry['total_items']} items reused")
    else:
        print("No embedded item reuse detected")


def fields_command(args):
    """List all translatable fields in a file"""
    file_path = Path(args.file)
    
    if not file_path.exists():
        print(f"Error: File '{args.file}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    entries = data.get('entries', {})
    
    print(f"Translatable fields in {args.file}:")
    print("=" * 50)
    
    for entry_name, entry_data in entries.items():
        fields = get_all_translatable_fields(entry_data)
        if fields:
            print(f"\n{entry_name}:")
            for field in sorted(fields):
                print(f"  - {field}")


if __name__ == "__main__":
    main()