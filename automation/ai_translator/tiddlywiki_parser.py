#!/usr/bin/env python3
"""Extract comprehensive translation memory from TiddlyWiki for SWADE."""
import json
import os
import re
from pathlib import Path

def find_tw_path():
    """Locate the TiddlyWiki HTML file."""
    script_dir = Path(__file__).resolve().parent
    swade_dir = script_dir.parent.parent  # swade_compendium_chn
    root_dir = swade_dir.parent  # swade_translation
    for search_dir in (root_dir, swade_dir):
        for f in search_dir.iterdir():
            if "Tiddly" in f.name and f.suffix == ".html":
                return f
    return None

def load_tiddlers(tw_path):
    """Load all tiddlers from TiddlyWiki HTML."""
    with open(tw_path, "rb") as fh:
        raw = fh.read()
    text = raw.decode("utf-8", errors="replace")
    
    store_pos = text.find('class="tiddlywiki-tiddler-store"')
    json_start = text.find("[", store_pos)
    script_end = text.find("</script>", json_start)
    segment = text[json_start:script_end]
    
    # String-aware bracket matching
    depth = 0; in_string = False; escape = False; json_end = -1
    for i, ch in enumerate(segment):
        if escape: escape = False; continue
        if ch == "\\": escape = True; continue
        if ch == '"' and not escape: in_string = not in_string; continue
        if in_string: continue
        if ch == "[": depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0: json_end = i; break
    
    return json.loads(segment[:json_end + 1])

def extract_from_titles(tiddlers):
    """Extract English→Chinese term pairs from bilingual titles.
    
    Title patterns:
    - 传送__TELEPORT  (Chinese__ENGLISH)
    - 毒素__POISON
    - 专长与负赘_EDGES & HINDRANCES
    - 超级属性__SUPER_ATTRIBUTE
    """
    glossary = {}
    for t in tiddlers:
        title = t.get("title", "")
        # Pattern: Chinese__ENGLISH (double underscore)
        match = re.match(r'^.+__([A-Z][A-Z_\s&]+)$', title)
        if match:
            eng = match.group(1).strip().replace("_", " ").replace("  ", " ")
            # Get Chinese part: remove the __ENGLISH suffix
            chn = title[:match.start(1) - 2].strip()
            # Get last segment after /
            chn_last = chn.split("/")[-1] if "/" in chn else chn
            if chn_last and eng and len(chn_last) < 50 and len(eng) < 60:
                glossary[eng] = chn_last
        
        # Pattern: Chinese_ENGLISH (single underscore, but not with leading space)
        match2 = re.match(r'^.+_([A-Z][A-Za-z_\s&]+)$', title)
        if match2:
            eng = match2.group(1).strip().replace("_", " ").replace("  ", " ")
            if eng and len(eng) > 2 and len(eng) < 60:
                chn = title[:match2.start(1) - 1].strip()
                chn_last = chn.split("/")[-1] if "/" in chn else chn
                if chn_last and len(chn_last) < 50:
                    if eng not in glossary:
                        glossary[eng] = chn_last
    
    return glossary

def extract_wiki_links(text):
    """Extract [[English|Chinese]] or [[Chinese]] wiki links."""
    pairs = []
    for m in re.finditer(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', text):
        target = m.group(1).strip()
        display = m.group(2).strip() if m.group(2) else target
        pairs.append((target, display))
    return pairs

def build_enhanced_glossary(tw_path):
    """Main function: build glossary from TiddlyWiki."""
    print(f"Loading tiddlers from {tw_path}...")
    tiddlers = load_tiddlers(tw_path)
    print(f"Loaded {len(tiddlers)} tiddlers")
    
    # Load existing glossary
    swade_dir = Path(__file__).resolve().parent.parent.parent
    glossary_path = swade_dir / "glossary" / "swade-glossary.json"
    existing = {}
    if glossary_path.exists():
        with open(glossary_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        print(f"Existing glossary: {len(existing)} terms")
    
    # Extract from titles
    title_glossary = extract_from_titles(tiddlers)
    print(f"Extracted from titles: {len(title_glossary)} terms")
    
    # Filter: skip very short or very long, skip existing matches
    new_terms = {}
    for eng, chn in title_glossary.items():
        if eng in existing:
            continue
        if len(eng) < 3 or len(chn) < 1:
            continue
        if len(eng) > 60 or len(chn) > 50:
            continue
        # Skip if it looks like English in Chinese field
        if re.match(r'^[A-Za-z\s]+$', chn):
            continue
        new_terms[eng] = chn
    
    print(f"New unique terms: {len(new_terms)}")
    
    # Merge: existing takes priority
    merged = dict(new_terms)
    merged.update(existing)
    print(f"Merged glossary: {len(merged)} terms")
    
    # Save
    out_dir = swade_dir / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    with open(out_dir / "enhanced_glossary.json", "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    
    with open(out_dir / "new_tw_terms.json", "w", encoding="utf-8") as f:
        json.dump(new_terms, f, ensure_ascii=False, indent=2)
    
    # Print some new terms
    print(f"\n=== Sample new terms (30 of {len(new_terms)}) ===")
    for i, (k, v) in enumerate(list(new_terms.items())[:30]):
        print(f"  {k:40s} → {v}")
    
    return merged

if __name__ == "__main__":
    tw_path = find_tw_path()
    if tw_path:
        build_enhanced_glossary(tw_path)
    else:
        print("ERROR: TiddlyWiki HTML not found")
