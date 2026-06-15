#!/usr/bin/env python3
"""Enhanced compendium .db to Babele JSON converter.

Handles FoundryVTT compendium pack files (.db), which are newline-delimited JSON (ndjson).
Converts them to Babele-compatible translation JSON format.

Usage:
    # Convert a single .db file
    python db_converter.py path/to/pack.db --type Item --mapping mappings/edges.json

    # Batch convert all .db files in a directory
    python db_converter.py path/to/packs/ --batch --output en-US/

    # Auto-detect pack type and generate mapping
    python db_converter.py path/to/pack.db --auto
"""
import json
import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any


# Known translatable fields by document type
TRANSLATABLE_BY_TYPE = {
    "Item": [
        "name", "system.description",
        "system.notes", "system.category",
        "system.range", "system.duration",
        "system.trapping", "system.rank",
    ],
    "Actor": [
        "name", "system.details.biography.value",
        "system.details.appearance", "system.details.notes",
        "system.details.goals", "system.details.archetype",
        "system.details.species.name", "system.category",
    ],
    "JournalEntry": [
        "name", "pages.*.name", "pages.*.text",
        "pages.*.image.caption",
    ],
    "Scene": [
        "name", "notes",
    ],
    "RollTable": [
        "name", "description",
        "results.*.text",
    ],
    "Macro": [
        "name", "command",
    ],
    "Cards": [
        "name", "description",
    ],
    "Playlist": [
        "name", "description",
    ],
}


def get_nested_value(data: dict, path: str) -> Optional[Any]:
    """Get a value from a nested dict using dot notation.
    
    Supports wildcards: 'pages.*.name' matches all page names.
    """
    parts = path.split(".")
    current = data
    
    for i, part in enumerate(parts):
        if part == "*":
            # Wildcard: return dict of all sub-values
            if isinstance(current, dict):
                remaining = ".".join(parts[i+1:])
                result = {}
                for key, value in current.items():
                    if remaining:
                        val = get_nested_value(value, remaining)
                        if val is not None:
                            result[key] = val
                    else:
                        result[key] = value
                return result if result else None
            elif isinstance(current, list):
                remaining = ".".join(parts[i+1:])
                result = []
                for item in current:
                    if remaining:
                        val = get_nested_value(item, remaining)
                        if val is not None:
                            result.append(val)
                return result if result else None
            return None
        
        if isinstance(current, dict):
            current = current.get(part)
            if current is None:
                return None
        else:
            return None
    
    return current


def extract_translatable_fields(document: dict, doc_type: str) -> dict:
    """Extract all translatable fields from a document."""
    fields = TRANSLATABLE_BY_TYPE.get(doc_type, ["name"])
    
    result = {}
    for field_path in fields:
        value = get_nested_value(document, field_path)
        if value is not None and value != "":
            # Use the last part of the path as the field name
            field_name = field_path.split(".")[-1]
            # Handle wildcard results
            if isinstance(value, dict):
                for sub_key, sub_val in value.items():
                    if isinstance(sub_val, str) and sub_val.strip():
                        result[f"{field_name}.{sub_key}"] = sub_val
            elif isinstance(value, list):
                for idx, item in enumerate(value):
                    if isinstance(item, str) and item.strip():
                        result[f"{field_name}.{idx}"] = item
            elif isinstance(value, str) and value.strip():
                result[field_name] = value
            else:
                result[field_name] = value
    
    return result


def read_db_file(db_path: Path) -> List[dict]:
    """Read a FoundryVTT .db compendium file (ndjson format)."""
    documents = []
    with open(db_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                doc = json.loads(line)
                documents.append(doc)
            except json.JSONDecodeError as e:
                print(f"  Warning: Skipping invalid JSON line: {e}")
    return documents


def convert_to_babele(
    documents: List[dict],
    doc_type: str,
    label: str = "",
    existing_mapping: Optional[dict] = None,
) -> dict:
    """Convert documents to Babele-compatible translation JSON format.
    
    Args:
        documents: List of document dicts from .db file.
        doc_type: Type of documents (Item, Actor, JournalEntry, etc.).
        label: Label for the compendium.
        existing_mapping: Optional existing Babele mapping config.
    
    Returns:
        Babele-format dict with 'label', 'mapping', and 'entries'.
    """
    if not label:
        label = "Compendium"

    # Build mapping
    mapping = existing_mapping or {}
    if not mapping:
        # Generate basic mapping
        mapping = build_auto_mapping(doc_type)

    # Build entries
    entries = {}
    for doc in documents:
        doc_name = doc.get("name", "")
        if not doc_name:
            continue

        if doc_name in entries:
            # Duplicate name: append _id suffix
            doc_name = f"{doc_name}_{doc.get('_id', '')[:8]}"

        entry_data = {"name": doc_name}
        
        # Extract translatable fields
        translatable = extract_translatable_fields(doc, doc_type)
        entry_data.update(translatable)

        # Handle JournalEntry pages
        if doc_type == "JournalEntry" and "pages" in doc:
            pages = {}
            for page in doc.get("pages", []):
                page_name = page.get("name", "")
                page_entry = {"name": page_name}
                
                if "text" in page and page["text"]:
                    page_entry["text"] = page["text"]
                if "image" in page and isinstance(page["image"], dict):
                    caption = page["image"].get("caption")
                    if caption:
                        page_entry.setdefault("image", {})
                        page_entry["image"]["caption"] = caption
                
                page_id = page.get("_id", page_name)
                pages[page_id] = page_entry
            
            if pages:
                entry_data["pages"] = pages

        entries[doc_name] = entry_data

    return {
        "label": label,
        "mapping": mapping,
        "entries": entries,
    }


def build_auto_mapping(doc_type: str) -> dict:
    """Build a basic field mapping for a document type."""
    base_mapping = {
        "name": "name",
    }
    
    field_paths = TRANSLATABLE_BY_TYPE.get(doc_type, ["name"])
    for path in field_paths:
        if path == "name":
            continue
        # Use last segment as key
        key = path.split(".")[-1]
        base_mapping[key] = path
    
    return base_mapping


def detect_pack_type(documents: List[dict]) -> str:
    """Auto-detect the pack type from document structure."""
    if not documents:
        return "Item"
    
    doc = documents[0]
    
    if "pages" in doc:
        return "JournalEntry"
    if "system" in doc:
        system = doc.get("system", {})
        if "details" in system and "biography" in system.get("details", {}):
            return "Actor"
        if "actions" in system or "requirements" in system:
            return "Item"
        # Check common item fields
        if any(k in system for k in ("category", "description", "notes")):
            return "Item"
    if "results" in doc:
        return "RollTable"
    if "command" in doc:
        return "Macro"
    
    return "Item"


def convert_file(
    db_path: Path,
    output_path: Optional[Path] = None,
    doc_type: Optional[str] = None,
    label: Optional[str] = None,
    mapping_file: Optional[Path] = None,
) -> dict:
    """Convert a single .db file to Babele JSON.
    
    Returns the converted data dict.
    """
    print(f"Reading: {db_path}")
    documents = read_db_file(db_path)
    print(f"  Found {len(documents)} documents")

    if not documents:
        print("  Warning: No documents found")
        return {}

    # Auto-detect type
    if not doc_type:
        doc_type = detect_pack_type(documents)
        print(f"  Auto-detected type: {doc_type}")

    # Load existing mapping
    existing_mapping = None
    if mapping_file and mapping_file.exists():
        with open(mapping_file, "r", encoding="utf-8") as f:
            mapping_data = json.load(f)
            existing_mapping = mapping_data.get("mapping", {})

    # Determine label
    if not label:
        label = db_path.stem

    # Convert
    babele_data = convert_to_babele(documents, doc_type, label, existing_mapping)

    # Write output
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(babele_data, f, ensure_ascii=False, indent=2)
        print(f"  Output: {output_path} ({len(babele_data['entries'])} entries)")

    return babele_data


def batch_convert(
    db_dir: Path,
    output_dir: Path,
    doc_type: Optional[str] = None,
    pattern: str = "*.db",
) -> List[Path]:
    """Convert all .db files in a directory."""
    output_files = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for db_file in sorted(db_dir.glob(pattern)):
        output_name = db_file.stem + ".json"
        output_path = output_dir / output_name
        convert_file(db_file, output_path, doc_type=doc_type)
        output_files.append(output_path)

    print(f"\nBatch complete: {len(output_files)} files converted")
    return output_files


def main():
    parser = argparse.ArgumentParser(
        description="Convert FoundryVTT compendium .db files to Babele JSON"
    )
    parser.add_argument("path", help="Path to .db file or directory")
    parser.add_argument("--output", "-o", help="Output file or directory")
    parser.add_argument("--type", "-t", help="Document type (Item, Actor, JournalEntry, etc.)")
    parser.add_argument("--label", "-l", help="Compendium label")
    parser.add_argument("--mapping", "-m", help="Path to mapping JSON file")
    parser.add_argument("--batch", "-b", action="store_true", help="Batch convert directory")
    parser.add_argument("--auto", "-a", action="store_true", help="Auto-detect pack type")

    args = parser.parse_args()
    path = Path(args.path)

    if not path.exists():
        print(f"Error: Path not found: {path}")
        sys.exit(1)

    doc_type = args.type
    if args.auto:
        doc_type = None

    if path.is_dir() or args.batch:
        output_dir = Path(args.output) if args.output else Path("en-US")
        batch_convert(path, output_dir, doc_type=doc_type)
    else:
        output_path = Path(args.output) if args.output else path.with_suffix(".json")
        mapping_file = Path(args.mapping) if args.mapping else None
        convert_file(path, output_path, doc_type=doc_type, 
                    label=args.label, mapping_file=mapping_file)


if __name__ == "__main__":
    main()
