"""Build translation memory index from existing zh_Hans/ translations.

Creates a fast lookup index mapping English entry names to their
Chinese translations across all compendiums. This serves as:
1. A translation memory for the AI (reuse existing translations)
2. A source for few-shot examples (pair English source with Chinese target)
"""
import json
from pathlib import Path
from typing import Dict, List, Optional


def build_translation_memory(
    en_dir: Path,
    zh_dir: Path,
    max_examples_per_file: int = 5,
) -> Dict:
    """Build translation memory from en-US/ and zh_Hans/ paired files.

    Returns a dict with:
    - memory: {entry_name: {field: chinese_translation}}
    - examples: [{english_html, chinese_html, entry_name, field}] for few-shot
    """
    memory: Dict[str, Dict[str, str]] = {}
    examples: List[Dict] = []

    en_files = sorted(en_dir.glob("*.json"))
    
    for en_file in en_files:
        zh_file = zh_dir / en_file.name
        if not zh_file.exists():
            continue

        try:
            with open(en_file, "r", encoding="utf-8") as f:
                en_data = json.load(f)
            with open(zh_file, "r", encoding="utf-8") as f:
                zh_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        en_entries = en_data.get("entries", {})
        zh_entries = zh_data.get("entries", {})

        file_examples = 0
        for entry_name, en_entry in en_entries.items():
            if entry_name not in zh_entries:
                continue
            
            zh_entry = zh_entries[entry_name]
            entry_memory = {}
            
            for field in ("name", "description", "text", "category", 
                         "biography", "notes", "appearance", "archetype",
                         "trapping", "range", "duration", "rank"):
                en_val = en_entry.get(field)
                zh_val = zh_entry.get(field)
                
                if en_val and zh_val and en_val != zh_val:
                    entry_memory[field] = zh_val
                    
                    # Collect few-shot examples (prefer description/text fields)
                    if (field in ("description", "text", "biography") 
                        and file_examples < max_examples_per_file
                        and len(en_val) > 100 and len(zh_val) > 100):
                        examples.append({
                            "entry_name": entry_name,
                            "field": field,
                            "english": en_val,
                            "chinese": zh_val,
                            "source_file": en_file.name,
                        })
                        file_examples += 1
            
            if entry_memory:
                memory[entry_name] = entry_memory

        print(f"  {en_file.name}: {len(entry_memory) if 'entry_memory' in dir() else 0} entries, "
              f"{file_examples} examples")

    return {
        "memory": memory,
        "examples": examples,
        "total_entries": len(memory),
        "total_examples": len(examples),
    }


def build_few_shot_index(examples: List[Dict], glossary: Dict[str, str]) -> List[Dict]:
    """Score and rank few-shot examples by relevance.

    Higher score = more glossary terms in the text = better teaching example.
    """
    scored = []
    for ex in examples:
        # Count glossary terms appearing in English text
        term_count = sum(1 for term in glossary if term.lower() in ex["english"].lower())
        # Prefer medium-length examples
        length_score = min(len(ex["english"]), 2000) / 2000
        score = term_count * 2 + length_score
        scored.append({**ex, "score": score, "term_count": term_count})
    
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def main():
    en_dir = Path(__file__).resolve().parent.parent.parent / "en-US"
    zh_dir = Path(__file__).resolve().parent.parent.parent / "zh_Hans"
    glossary_path = Path(__file__).resolve().parent.parent.parent / "data" / "enhanced_glossary.json"
    out_dir = Path(__file__).resolve().parent.parent.parent / "data"

    print(f"Building translation memory...")
    print(f"  Source: {en_dir}")
    print(f"  Target: {zh_dir}")

    # Load glossary
    glossary = {}
    if glossary_path.exists():
        with open(glossary_path, "r", encoding="utf-8") as f:
            glossary = json.load(f)
        print(f"  Glossary: {len(glossary)} terms")

    # Build memory
    result = build_translation_memory(en_dir, zh_dir)
    print(f"\nTotal translation entries: {result['total_entries']}")
    print(f"Total few-shot candidates: {result['total_examples']}")

    # Build scored few-shot index
    scored_examples = build_few_shot_index(result["examples"], glossary)
    print(f"Top examples by glossary coverage:")

    # Save full memory
    memory_path = out_dir / "translation_memory.json"
    with open(memory_path, "w", encoding="utf-8") as f:
        json.dump(result["memory"], f, ensure_ascii=False)
    print(f"\nSaved: {memory_path}")

    # Save top few-shot examples (top 50)
    top_examples = scored_examples[:50]
    examples_path = out_dir / "few_shot_examples.json"
    with open(examples_path, "w", encoding="utf-8") as f:
        json.dump(top_examples, f, ensure_ascii=False, indent=2)
    print(f"Saved: {examples_path} ({len(top_examples)} examples)")


if __name__ == "__main__":
    main()
