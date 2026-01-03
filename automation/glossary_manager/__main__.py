#!/usr/bin/env python3
"""
Glossary Manager CLI Entry Point

Usage:
    python -m automation.glossary_manager apply GLOSSARY_FILE TEXT_FILE [--output OUTPUT_FILE]
    python -m automation.glossary_manager find-missing GLOSSARY_FILE TEXT_FILE [--format FORMAT]
    python -m automation.glossary_manager update GLOSSARY_FILE TERM TRANSLATION
    python -m automation.glossary_manager export GLOSSARY_FILE OUTPUT_FILE [--format FORMAT]
    python -m automation.glossary_manager import GLOSSARY_FILE INPUT_FILE [--merge]
    
Examples:
    # Apply glossary to text
    python -m automation.glossary_manager apply glossary/swade-glossary.json input.txt --output translated.txt
    
    # Find missing terms in text
    python -m automation.glossary_manager find-missing glossary/swade-glossary.json input.txt --format markdown
    
    # Update a term in glossary
    python -m automation.glossary_manager update glossary/swade-glossary.json "Edge" "专长"
    
    # Export glossary to CSV
    python -m automation.glossary_manager export glossary/swade-glossary.json output.csv --format csv
    
    # Import terms from CSV
    python -m automation.glossary_manager import glossary/swade-glossary.json new-terms.csv --merge
"""

import argparse
import sys
from pathlib import Path

from .manager import GlossaryManager


def main():
    parser = argparse.ArgumentParser(
        description="Manage translation glossaries and apply term translations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Apply command
    apply_parser = subparsers.add_parser(
        'apply',
        help='Apply glossary terms to text'
    )
    apply_parser.add_argument(
        'glossary',
        help='Glossary JSON file'
    )
    apply_parser.add_argument(
        'text_file',
        help='Text file to process'
    )
    apply_parser.add_argument(
        '--output',
        help='Output file (default: stdout)'
    )
    apply_parser.add_argument(
        '--track',
        action='store_true',
        help='Show replacement statistics'
    )
    
    # Find missing command
    missing_parser = subparsers.add_parser(
        'find-missing',
        help='Find missing terms in text'
    )
    missing_parser.add_argument(
        'glossary',
        help='Glossary JSON file'
    )
    missing_parser.add_argument(
        'text_file',
        help='Text file to analyze'
    )
    missing_parser.add_argument(
        '--format',
        choices=['text', 'markdown', 'json'],
        default='text',
        help='Output format (default: text)'
    )
    missing_parser.add_argument(
        '--output',
        help='Output file (default: stdout)'
    )
    
    # Update command
    update_parser = subparsers.add_parser(
        'update',
        help='Update a term in glossary'
    )
    update_parser.add_argument(
        'glossary',
        help='Glossary JSON file'
    )
    update_parser.add_argument(
        'term',
        help='English term to update'
    )
    update_parser.add_argument(
        'translation',
        help='Chinese translation'
    )
    update_parser.add_argument(
        '--sync-translations',
        help='Directory containing translation files to update'
    )
    
    # Export command
    export_parser = subparsers.add_parser(
        'export',
        help='Export glossary to different formats'
    )
    export_parser.add_argument(
        'glossary',
        help='Glossary JSON file'
    )
    export_parser.add_argument(
        'output',
        help='Output file'
    )
    export_parser.add_argument(
        '--format',
        choices=['json', 'csv', 'md'],
        default='json',
        help='Output format (default: json)'
    )
    
    # Import command
    import_parser = subparsers.add_parser(
        'import',
        help='Import terms from file'
    )
    import_parser.add_argument(
        'glossary',
        help='Glossary JSON file'
    )
    import_parser.add_argument(
        'input',
        help='Input file (JSON or CSV)'
    )
    import_parser.add_argument(
        '--merge',
        action='store_true',
        help='Merge with existing glossary (default: replace)'
    )
    
    # List command
    list_parser = subparsers.add_parser(
        'list',
        help='List all terms in glossary'
    )
    list_parser.add_argument(
        'glossary',
        help='Glossary JSON file'
    )
    list_parser.add_argument(
        '--filter',
        help='Filter terms containing this text'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == 'apply':
            apply_command(args)
        elif args.command == 'find-missing':
            find_missing_command(args)
        elif args.command == 'update':
            update_command(args)
        elif args.command == 'export':
            export_command(args)
        elif args.command == 'import':
            import_command(args)
        elif args.command == 'list':
            list_command(args)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def apply_command(args):
    """Apply glossary to text file"""
    glossary_path = Path(args.glossary)
    text_path = Path(args.text_file)
    
    if not glossary_path.exists():
        print(f"Error: Glossary file '{args.glossary}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    if not text_path.exists():
        print(f"Error: Text file '{args.text_file}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    manager = GlossaryManager(args.glossary)
    
    # Read input text
    text = text_path.read_text(encoding='utf-8')
    
    print(f"Applying glossary with {len(manager)} terms to '{args.text_file}'...", file=sys.stderr)
    
    if args.track:
        result, replacements = manager.apply_glossary_with_tracking(text)
        
        # Show replacement statistics
        if replacements:
            print("Replacement statistics:", file=sys.stderr)
            for term, count in sorted(replacements.items()):
                print(f"  {term}: {count} replacements", file=sys.stderr)
            total_replacements = sum(replacements.values())
            print(f"Total: {total_replacements} replacements", file=sys.stderr)
        else:
            print("No terms were replaced", file=sys.stderr)
    else:
        result = manager.apply_glossary(text)
    
    # Output result
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result, encoding='utf-8')
        print(f"✓ Result saved to '{args.output}'", file=sys.stderr)
    else:
        print(result)


def find_missing_command(args):
    """Find missing terms in text"""
    glossary_path = Path(args.glossary)
    text_path = Path(args.text_file)
    
    if not glossary_path.exists():
        print(f"Error: Glossary file '{args.glossary}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    if not text_path.exists():
        print(f"Error: Text file '{args.text_file}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    manager = GlossaryManager(args.glossary)
    text = text_path.read_text(encoding='utf-8')
    
    print(f"Analyzing '{args.text_file}' for missing terms...", file=sys.stderr)
    
    missing_terms = manager.find_missing_terms(text)
    
    if args.format == 'markdown':
        output = manager.generate_missing_terms_report(text)
    elif args.format == 'json':
        import json
        output = json.dumps({
            'missing_terms': missing_terms,
            'count': len(missing_terms)
        }, ensure_ascii=False, indent=2)
    else:
        # Text format
        if missing_terms:
            lines = [f"Found {len(missing_terms)} missing terms:"]
            for term in missing_terms:
                suggestions = manager.suggest_translations(term)
                suggestion = f" -> {suggestions[0]}" if suggestions else ""
                lines.append(f"  {term}{suggestion}")
            output = "\n".join(lines)
        else:
            output = "No missing terms found."
    
    # Output result
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding='utf-8')
        print(f"✓ Report saved to '{args.output}'", file=sys.stderr)
    else:
        print(output)


def update_command(args):
    """Update a term in glossary"""
    manager = GlossaryManager(args.glossary)
    
    old_translation = manager.get_translation(args.term)
    
    if args.sync_translations and old_translation:
        # Update glossary and sync translation files
        result = manager.update_term_and_translations(
            args.term, 
            args.translation, 
            args.sync_translations
        )
        
        print(f"✓ Updated term '{args.term}': '{old_translation}' -> '{args.translation}'")
        
        if result.updated_files:
            print(f"✓ Updated {len(result.updated_files)} translation files:")
            for file_path in result.updated_files:
                print(f"  - {file_path}")
            print(f"✓ Total entries updated: {result.updated_entries}")
        
        if result.errors:
            print("Errors occurred:", file=sys.stderr)
            for error in result.errors:
                print(f"  - {error}", file=sys.stderr)
    else:
        # Just update glossary
        manager.update_glossary(args.term, args.translation)
        
        if old_translation:
            print(f"✓ Updated term '{args.term}': '{old_translation}' -> '{args.translation}'")
        else:
            print(f"✓ Added new term '{args.term}': '{args.translation}'")


def export_command(args):
    """Export glossary to different formats"""
    manager = GlossaryManager(args.glossary)
    
    print(f"Exporting {len(manager)} terms to '{args.output}' in {args.format} format...", file=sys.stderr)
    
    manager.export_glossary(args.output, args.format)
    
    print(f"✓ Glossary exported to '{args.output}'", file=sys.stderr)


def import_command(args):
    """Import terms from file"""
    manager = GlossaryManager(args.glossary)
    
    original_count = len(manager)
    
    print(f"Importing terms from '{args.input}'...", file=sys.stderr)
    
    imported_count = manager.import_glossary(args.input, args.merge)
    
    new_count = len(manager)
    
    print(f"✓ Imported {imported_count} terms", file=sys.stderr)
    print(f"✓ Glossary now contains {new_count} terms (was {original_count})", file=sys.stderr)


def list_command(args):
    """List all terms in glossary"""
    manager = GlossaryManager(args.glossary)
    
    all_terms = manager.get_all_terms()
    
    if args.filter:
        # Filter terms containing the specified text
        filter_text = args.filter.lower()
        filtered_terms = {
            k: v for k, v in all_terms.items() 
            if filter_text in k.lower() or filter_text in v.lower()
        }
        print(f"Terms matching '{args.filter}' ({len(filtered_terms)} of {len(all_terms)}):")
        terms_to_show = filtered_terms
    else:
        print(f"All terms in glossary ({len(all_terms)}):")
        terms_to_show = all_terms
    
    for term, translation in sorted(terms_to_show.items()):
        print(f"  {term} -> {translation}")


if __name__ == "__main__":
    main()