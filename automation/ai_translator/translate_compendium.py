#!/usr/bin/env python3
"""CLI for translating SWADE compendiums with DeepSeek v4.

Usage:
    # Set API key
    export DEEPSEEK_API_KEY=sk-xxx

    # Translate a single file
    python -m automation.ai_translator.translate_compendium \\
        en-US/swade-core-rules.swade-edges.json \\
        --output zh_Hans/swade-core-rules.swade-edges.json

    # Translate entire directory
    python -m automation.ai_translator.translate_compendium \\
        --dir en-US/ --target zh_Hans/

    # Dry run (estimate cost, no actual API calls)
    python -m automation.ai_translator.translate_compendium \\
        --dir en-US/ --dry-run

    # Translate with glossary injection
    python -m automation.ai_translator.translate_compendium \\
        --dir en-US/ --target zh_Hans/ \\
        --glossary data/enhanced_glossary.json \\
        --few-shot data/few_shot_examples.json
"""
import argparse
import logging
import os
import sys
from pathlib import Path

# Ensure the automation package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from automation.ai_translator.client import DeepSeekClient, create_client_from_env
from automation.ai_translator.translator import (
    CompendiumTranslator,
    translate_directory,
)
from automation.ai_translator.prompts import PromptBuilder


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def cmd_translate_file(args):
    """Translate a single compendium file."""
    input_path = Path(args.file)
    output_path = Path(args.output) if args.output else None

    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    client = create_client_from_env()
    prompt_builder = PromptBuilder(
        glossary_path=Path(args.glossary) if args.glossary else None,
        few_shot_path=Path(args.few_shot) if args.few_shot else None,
    )

    translator = CompendiumTranslator(
        client=client,
        prompt_builder=prompt_builder,
        dry_run=args.dry_run,
    )

    result = translator.translate_file(input_path, output_path)
    if result:
        entries = len(result.get("entries", {}))
        print(f"\n✓ Translation complete: {entries} entries")
        print(f"  Fields translated: {translator.stats['fields_translated']}")
        print(f"  Chunks translated: {translator.stats['chunks_translated']}")
        if translator.stats["validation_failures"]:
            print(f"  ⚠ Validation issues: {translator.stats['validation_failures']}")


def cmd_translate_dir(args):
    """Translate all compendium files in a directory."""
    en_dir = Path(args.dir)
    zh_dir = Path(args.target)

    if not en_dir.exists():
        print(f"Error: Directory not found: {en_dir}")
        sys.exit(1)

    zh_dir.mkdir(parents=True, exist_ok=True)

    summary = translate_directory(
        en_dir=en_dir,
        zh_dir=zh_dir,
        glossary_path=Path(args.glossary) if args.glossary else None,
        few_shot_path=Path(args.few_shot) if args.few_shot else None,
        dry_run=args.dry_run,
    )

    print(f"\n✓ Directory translation complete")
    print(f"  Files: {summary['files_processed']}")
    print(f"  Entries: {summary['total_entries']}")
    print(f"  Fields: {summary['total_fields']}")


def cmd_dry_run(args):
    """Estimate translation scope without making API calls."""
    import json

    en_dir = Path(args.dir) if args.dir else Path("en-US")
    if not en_dir.exists():
        print(f"Error: Directory not found: {en_dir}")
        sys.exit(1)

    total_chars = 0
    total_entries = 0
    total_fields = 0
    file_stats = []

    for en_file in sorted(en_dir.glob("*.json")):
        if en_file.name == "___.json":
            continue

        with open(en_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        entries = data.get("entries", {})
        file_chars = 0
        file_fields = 0

        for entry_name, entry_data in entries.items():
            total_entries += 1
            for field in ("name", "description", "text", "category",
                         "biography", "notes", "appearance", "archetype"):
                value = entry_data.get(field, "")
                if value and isinstance(value, str):
                    total_chars += len(value)
                    file_chars += len(value)
                    file_fields += 1
                    total_fields += 1

            # Handle pages
            if "pages" in entry_data:
                for page_id, page_data in entry_data["pages"].items():
                    text = page_data.get("text", "")
                    if text:
                        total_chars += len(text)
                        file_chars += len(text)
                        file_fields += 1
                        total_fields += 1
                    name = page_data.get("name", "")
                    if name:
                        total_chars += len(name)
                        file_chars += len(name)

        file_stats.append({
            "file": en_file.name,
            "entries": len(entries),
            "chars": file_chars,
            "fields": file_fields,
        })

    # Rough cost estimate (DeepSeek: ~$0.14/1M input tokens, ~$0.28/1M output)
    input_tokens = total_chars // 4  # rough estimate
    output_tokens = total_chars // 3  # Chinese is more compact
    cost_est = (input_tokens / 1_000_000) * 0.14 + (output_tokens / 1_000_000) * 0.28

    print(f"\n=== Translation Scope Estimate ===")
    print(f"Files:       {len(file_stats)}")
    print(f"Entries:     {total_entries}")
    print(f"Fields:      {total_fields}")
    print(f"Total chars: {total_chars:,}")
    print(f"Est. tokens: {input_tokens + output_tokens:,} (in+out)")
    print(f"Est. cost:   ${cost_est:.3f} USD")

    if args.verbose:
        print(f"\nPer-file breakdown:")
        for fs in file_stats:
            print(f"  {fs['file']:50s} {fs['entries']:4d} entries  "
                  f"{fs['fields']:4d} fields  {fs['chars']:>10,} chars")


def main():
    parser = argparse.ArgumentParser(
        description="Translate SWADE compendiums using DeepSeek v4",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s en-US/swade-core-rules.swade-edges.json -o zh_Hans/swade-core-rules.swade-edges.json
  %(prog)s --dir en-US/ --target zh_Hans/
  %(prog)s --dir en-US/ --dry-run --verbose
  %(prog)s --dir en-US/ --target zh_Hans/ --glossary data/enhanced_glossary.json
        """,
    )
    sub = parser.add_subparsers(dest="command", help="Commands")

    # translate-file
    p_file = sub.add_parser("file", help="Translate a single file")
    p_file.add_argument("file", help="Path to en-US JSON file")
    p_file.add_argument("--output", "-o", help="Output path for translated JSON")
    p_file.add_argument("--glossary", help="Path to glossary JSON")
    p_file.add_argument("--few-shot", help="Path to few-shot examples JSON")
    p_file.add_argument("--dry-run", action="store_true", help="Preview without API calls")

    # translate-dir
    p_dir = sub.add_parser("dir", help="Translate a directory")
    p_dir.add_argument("--dir", default="en-US/", help="Source directory (default: en-US/)")
    p_dir.add_argument("--target", default="zh_Hans/", help="Target directory (default: zh_Hans/)")
    p_dir.add_argument("--glossary", help="Path to glossary JSON")
    p_dir.add_argument("--few-shot", help="Path to few-shot examples JSON")
    p_dir.add_argument("--dry-run", action="store_true", help="Preview without API calls")

    # dry-run
    p_dry = sub.add_parser("estimate", help="Estimate scope and cost")
    p_dry.add_argument("--dir", default="en-US/", help="Source directory")

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--file", help="Single file to translate (shorthand)")
    parser.add_argument("--output", "-o", help="Output file")
    parser.add_argument("--target", help="Target directory for --dir")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--glossary", help="Glossary JSON path")
    parser.add_argument("--few-shot", help="Few-shot examples JSON path")
    parser.add_argument("--dir", help="Source directory")

    args = parser.parse_args()
    setup_logging(getattr(args, 'verbose', False))

    # Handle shorthand mode (no subcommand)
    if not args.command:
        if getattr(args, 'dry_run', False) and not getattr(args, 'file', None):
            cmd_dry_run(args)
        elif getattr(args, 'file', None):
            cmd_translate_file(args)
        elif getattr(args, 'dir', None):
            cmd_translate_dir(args)
        else:
            parser.print_help()
    elif args.command == "file":
        cmd_translate_file(args)
    elif args.command == "dir":
        cmd_translate_dir(args)
    elif args.command == "estimate":
        cmd_dry_run(args)


if __name__ == "__main__":
    main()
