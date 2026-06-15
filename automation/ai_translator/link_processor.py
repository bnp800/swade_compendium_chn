"""Link post-processor for SWADE translations.

After AI translation, replaces @UUID and @Compendium link display text
with Chinese translations from the glossary. Also updates @Compendium
ref path names.
"""
import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class LinkReplacement:
    link_type: str
    original: str
    replaced: str
    english_term: str = ""
    chinese_term: str = ""
    matched: bool = True


@dataclass
class ProcessResult:
    file_path: str = ""
    total_links: int = 0
    replaced_links: int = 0
    unmatched_links: int = 0
    replacements: List = field(default_factory=list)
    unmatched_terms: List[str] = field(default_factory=list)


class LinkPostProcessor:

    def __init__(self, glossary):
        self.glossary = glossary
        self._lower = {k.lower(): v for k, v in glossary.items()}

    def _lookup(self, term):
        if not term:
            return None
        if term in self.glossary:
            return self.glossary[term]
        t = term.lower()
        if t in self._lower:
            return self._lower[t]
        s = term.strip()
        if s != term:
            if s in self.glossary:
                return self.glossary[s]
            if s.lower() in self._lower:
                return self._lower[s.lower()]
        return None

    def process_content(self, text):
        reps = []

        def uuid_fn(m):
            ref = m.group(1)
            disp = m.group(2)
            tr = self._lookup(disp)
            if tr:
                reps.append(LinkReplacement(
                    "uuid_display", m.group(0),
                    "@UUID[%s]{%s}" % (ref, tr),
                    disp, tr, True))
                return "@UUID[%s]{%s}" % (ref, tr)
            reps.append(LinkReplacement(
                "uuid_display", m.group(0), m.group(0), disp, matched=False))
            return m.group(0)

        def comp_fn(m):
            ref = m.group(1)
            disp = m.group(2)
            parts = ref.rsplit(".", 1)
            ename = parts[-1] if len(parts) == 2 else ref
            pref = parts[0] + "." if len(parts) == 2 else ""
            nt = self._lookup(ename)
            if disp is not None:
                dt = self._lookup(disp)
                nr = (pref + nt) if nt else ref
                nd = dt if dt else disp
                if nr != ref or nd != disp:
                    nl = "@Compendium[%s]{%s}" % (nr, nd)
                    reps.append(LinkReplacement(
                        "compendium_full", m.group(0), nl,
                        "%s|%s" % (ename, disp),
                        "%s|%s" % (nt or ename, dt or disp),
                        bool(nt or dt)))
                    return nl
                reps.append(LinkReplacement(
                    "compendium_full", m.group(0), m.group(0),
                    "%s|%s" % (ename, disp), matched=False))
            else:
                if nt:
                    nl = "@Compendium[%s%s]" % (pref, nt)
                    reps.append(LinkReplacement(
                        "compendium_bare", m.group(0), nl,
                        ename, nt, True))
                    return nl
                reps.append(LinkReplacement(
                    "compendium_bare", m.group(0), m.group(0),
                    ename, matched=False))
            return m.group(0)

        text = re.sub(r'@UUID\[([^\]]+)\]\{([^}]+)\}', uuid_fn, text)
        text = re.sub(r'@Compendium\[([^\]]+)\](?:\{([^}]*)\})?', comp_fn, text)
        return text, reps

    def process_file(self, filepath):
        logger.info("Processing: %s", filepath.name)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        result = ProcessResult(file_path=str(filepath))
        all_reps = []

        def walk(obj):
            nonlocal all_reps
            if isinstance(obj, dict):
                for k in list(obj.keys()):
                    v = obj[k]
                    if isinstance(v, str) and ("@UUID" in v or "@Compendium" in v):
                        new_v, reps = self.process_content(v)
                        obj[k] = new_v
                        all_reps.extend(reps)
                    elif isinstance(v, (dict, list)):
                        walk(v)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item)

        walk(data)

        result.total_links = len(all_reps)
        result.replacements = all_reps
        result.replaced_links = sum(1 for r in all_reps if r.matched)
        result.unmatched_links = result.total_links - result.replaced_links
        result.unmatched_terms = list(set(
            r.english_term for r in all_reps if not r.matched
        ))

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info("  Links: %d total, %d replaced, %d unmatched",
                     result.total_links, result.replaced_links, result.unmatched_links)
        if result.unmatched_terms:
            logger.warning("  Unmatched: %s", result.unmatched_terms[:10])
        return result

    def process_directory(self, d, pattern="*.json"):
        results = []
        for fp in sorted(d.glob(pattern)):
            if fp.name == "___.json":
                continue
            results.append(self.process_file(fp))
        total = sum(r.total_links for r in results)
        repd = sum(r.replaced_links for r in results)
        logger.info("Summary: %d files, %d links, %d replaced (%.1f%%)",
                     len(results), total, repd,
                     100 * repd / total if total else 0)
        return results
