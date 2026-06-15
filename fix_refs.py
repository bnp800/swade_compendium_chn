#!/usr/bin/env python3
"""Fix broken @Compendium ref paths in zh_Hans translation files.

Problem: zh_Hans has Chinese entry names in @Compendium ref paths
(e.g. swade-skills.运动) but FVTT compendium keys are English
(e.g. Athletics). This breaks links at runtime.

Fix: Replace Chinese ref names with English entry keys, keep
Chinese display text as-is.

Usage:
  python fix_refs.py zh_Hans --glossary data/enhanced_glossary.json --dry-run
  python fix_refs.py zh_Hans --glossary data/enhanced_glossary.json
"""
import json, re, shutil, argparse
from pathlib import Path


def build_lookup(glossary, zh_dir, en_dir):
    """Build Chinese->English lookup. Entry pairs take priority over glossary."""
    lookup = {}
    # FIRST: zh_Hans entry names -> en-US entry keys (these have correct case)
    for en_file in sorted(en_dir.glob("*.json")):
        if en_file.name == "___.json":
            continue
        zh_file = zh_dir / en_file.name
        if not zh_file.exists():
            continue
        with open(en_file, "r", encoding="utf-8") as f:
            en = json.load(f)
        with open(zh_file, "r", encoding="utf-8") as f:
            zh = json.load(f)
        for key in en.get("entries", {}):
            if key in zh.get("entries", {}):
                zn = zh["entries"][key].get("name", "")
                if zn and zn != key and zn not in lookup:
                    lookup[zn] = key
    # SECOND: glossary-derived terms (only fill gaps, entry pairs take priority)
    for eng, chn in glossary.items():
        if len(chn) >= 2 and len(eng) >= 2:
            if chn not in lookup:
                lookup[chn] = eng
            elif len(eng) < len(lookup[chn]):
                lookup[chn] = eng
    return lookup


def fix_text(text, lookup, cnt):
    """Fix Chinese @Compendium ref names to English."""
    def repl(m):
        ref = m.group(1)
        display = m.group(2)
        idx = ref.rfind(".")
        pack = ref[:idx] if idx > 0 else ""
        entry = ref[idx + 1:] if idx > 0 else ref
        if not re.search(r'[\u4e00-\u9fff]', entry):
            return m.group(0)
        eng = lookup.get(entry)
        if eng:
            nr = f"{pack}.{eng}" if pack else eng
            nl = f"@Compendium[{nr}]{{{display}}}" if display else f"@Compendium[{nr}]"
            cnt[0] += 1
            return nl
        cnt[1] += 1
        return m.group(0)
    return re.sub(r'@Compendium\[([^\]]+)\](?:\{([^}]*)\})?', repl, text)


def walk_fix(obj, lookup, cnt):
    """Recursively walk JSON structure and fix links."""
    if isinstance(obj, dict):
        for k in list(obj.keys()):
            v = obj[k]
            if isinstance(v, str) and "@Compendium" in v:
                obj[k] = fix_text(v, lookup, cnt)
            elif isinstance(v, (dict, list)):
                walk_fix(v, lookup, cnt)
    elif isinstance(obj, list):
        for item in obj:
            walk_fix(item, lookup, cnt)


def main():
    p = argparse.ArgumentParser(description="Fix broken @Compendium ref paths")
    p.add_argument("zh_dir", nargs="?", default="zh_Hans")
    p.add_argument("--glossary", default="data/enhanced_glossary.json")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    zh_dir = Path(args.zh_dir)
    en_dir = zh_dir.parent / "en-US"

    with open(args.glossary, "r", encoding="utf-8") as f:
        glossary = json.load(f)

    lookup = build_lookup(glossary, zh_dir, en_dir)
    print(f"Lookup: {len(lookup)} terms")

    if args.dry_run:
        total = 0
        fixable = 0
        for fp in sorted(zh_dir.glob("*.json")):
            if fp.name == "___.json":
                continue
            with open(fp, "r", encoding="utf-8") as f:
                content = f.read()
            for m in re.finditer(r'@Compendium\[([^\]]+)\]', content):
                ref = m.group(1)
                idx = ref.rfind(".")
                entry = ref[idx + 1:] if idx > 0 else ref
                if re.search(r'[\u4e00-\u9fff]', entry):
                    total += 1
                    if entry in lookup:
                        fixable += 1
        pct = 100 * fixable / total if total else 0
        print(f"Chinese @Compendium refs: {total}")
        print(f"Fixable: {fixable} ({pct:.1f}%)")
        print(f"Unfixable: {total - fixable}")
        return

    # Backup
    backup_dir = zh_dir.parent / "zh_Hans_backup"
    if not backup_dir.exists():
        shutil.copytree(str(zh_dir), str(backup_dir))
        print(f"Backup created: {backup_dir}")

    # Fix all files
    tf = tu = 0
    for fp in sorted(zh_dir.glob("*.json")):
        if fp.name == "___.json":
            continue
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        cnt = [0, 0]
        walk_fix(data, lookup, cnt)
        if cnt[0] > 0:
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  {fp.name}: {cnt[0]} fixed, {cnt[1]} unfixed")
        tf += cnt[0]
        tu += cnt[1]

    print(f"\nDone: {tf} fixed, {tu} unfixed")
    print(f"Backup at: {backup_dir}")


if __name__ == "__main__":
    main()
