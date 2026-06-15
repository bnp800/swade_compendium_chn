"""System prompt construction and post-translation validation for SWADE.

Builds rich prompts with glossary injection and few-shot examples,
then validates translations for correctness.
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Base system prompt template
BASE_SYSTEM_PROMPT = """You are an expert translator specializing in tabletop RPG content (Savage Worlds Adventure Edition / SWADE).

Translate the following English text to Simplified Chinese (zh-Hans).

CRITICAL RULES — follow exactly:
1. **Preserve ALL HTML tags, attributes, and CSS classes exactly as-is.** 
   Do NOT translate, modify, or remove any HTML tags, class names, or attributes.
   Example: <article class="swade-core"> stays as <article class="swade-core">

2. **Preserve ALL @UUID and @Compendium links exactly as-is.** 
   Do NOT translate, modify, or remove the content inside @UUID[...]{...} or @Compendium[...]{...} markers.
   These are FVTT hyperlinks and must remain unchanged.
   Example: @UUID[Compendium.swade-core-rules.swade-rules.xxx]{Smarts} stays EXACTLY as @UUID[Compendium.swade-core-rules.swade-rules.xxx]{Smarts}

3. **Preserve ALL HTML entities** (&rsquo;, &ldquo;, &mdash;, &shy;, etc.) exactly as they appear.

4. **Preserve ALL dice roll expressions** (like [[/r 1d4]]) exactly as they appear.

5. **Preserve ALL curly-brace placeholders** ({0}, {{variable}}, etc.) exactly as they appear.

6. **Use the provided glossary for game terminology.** The glossary below contains standard translations for SWADE terms. Always use these translations when the term appears.

7. **Match the tone:** Professional but accessible tabletop RPG rules text. Use natural Chinese gaming terminology.

8. **Output ONLY the translated text** — no explanations, notes, or markdown code fences. Just the translation.

{glossary_section}

{few_shot_section}
"""

GLOSSARY_SECTION = """=== STANDARD TERMINOLOGY GLOSSARY ===
Use these exact translations for game terms:
{glossary_text}
"""

FEW_SHOT_SECTION = """=== REFERENCE EXAMPLES ===
Here are examples of how similar content was translated:
{few_shot_text}
"""


class PromptBuilder:
    """Builds translation prompts with glossary and few-shot injection."""

    def __init__(
        self,
        glossary_path: Optional[Path] = None,
        few_shot_path: Optional[Path] = None,
        max_glossary_terms: int = 80,
        max_few_shot: int = 3,
    ):
        self.glossary: Dict[str, str] = {}
        self.few_shot_examples: List[Dict] = []
        self.max_glossary_terms = max_glossary_terms
        self.max_few_shot = max_few_shot

        if glossary_path and glossary_path.exists():
            with open(glossary_path, "r", encoding="utf-8") as f:
                self.glossary = json.load(f)

        if few_shot_path and few_shot_path.exists():
            with open(few_shot_path, "r", encoding="utf-8") as f:
                self.few_shot_examples = json.load(f)

    def select_relevant_terms(self, text: str) -> Dict[str, str]:
        """Select glossary terms that appear in the text."""
        relevant = {}
        text_lower = text.lower()
        for eng, chn in self.glossary.items():
            if len(eng) < 3:
                continue
            if eng.lower() in text_lower:
                relevant[eng] = chn
            if len(relevant) >= self.max_glossary_terms:
                break
        return relevant

    def select_relevant_examples(self, text: str) -> List[Dict]:
        """Select few-shot examples most relevant to the text."""
        text_lower = text.lower()
        scored = []
        for ex in self.few_shot_examples:
            english = ex.get("english", "")
            score = sum(1 for term in self.glossary
                       if term.lower() in english.lower() and term.lower() in text_lower)
            scored.append((score, ex))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [ex for _, ex in scored[:self.max_few_shot] if _ > 0]

    def build(self, text: str, field_type: str = "description") -> str:
        """Build a complete system prompt for translating the given text.

        Args:
            text: The text to translate.
            field_type: Type of field ('name', 'description', 'text', 'category').

        Returns:
            Complete system prompt string.
        """
        # Select relevant glossary terms
        relevant_terms = self.select_relevant_terms(text)
        glossary_text = ""
        if relevant_terms:
            term_lines = [f"  {eng} → {chn}"
                         for eng, chn in sorted(relevant_terms.items(),
                                                key=lambda x: len(x[0]), reverse=True)]
            glossary_text = "\n".join(term_lines)

        # Select relevant examples
        relevant_examples = self.select_relevant_examples(text)
        few_shot_text = ""
        if relevant_examples:
            example_strs = []
            for i, ex in enumerate(relevant_examples, 1):
                en_preview = ex["english"][:300]
                zh_preview = ex["chinese"][:300]
                example_strs.append(
                    f"Example {i} ({ex.get('entry_name', '')}):\n"
                    f"EN: {en_preview}...\n"
                    f"ZH: {zh_preview}..."
                )
            few_shot_text = "\n".join(example_strs)

        # Field-specific instructions
        field_hint = ""
        if field_type == "name":
            field_hint = "\nThis is an ITEM NAME. Keep it concise (typically 2-6 characters in Chinese)."
        elif field_type == "category":
            field_hint = "\nThis is a CATEGORY label. Keep it short (1-5 characters)."

        prompt = BASE_SYSTEM_PROMPT.format(
            glossary_section=GLOSSARY_SECTION.format(glossary_text=glossary_text) if glossary_text else "",
            few_shot_section=FEW_SHOT_SECTION.format(few_shot_text=few_shot_text) if few_shot_text else "",
        )
        
        if field_hint:
            prompt += field_hint

        return prompt


class TranslationValidator:
    """Validates translations for correctness and completeness."""

    @staticmethod
    def count_links(text: str) -> Tuple[int, int]:
        """Count @UUID and @Compendium links in text."""
        uuid_count = len(re.findall(r'@UUID\[', text))
        compendium_count = len(re.findall(r'@Compendium\[', text))
        return uuid_count, compendium_count

    @staticmethod
    def check_html_tags(source: str, translation: str) -> List[str]:
        """Check that HTML tags match between source and translation.

        Returns list of issues found (empty = good).
        """
        issues = []
        
        # Count tags
        source_tags = re.findall(r'</?(\w+)', source)
        trans_tags = re.findall(r'</?(\w+)', translation)

        source_open = [t for t in source_tags if not t.startswith('/')]
        source_close = [t[1:] for t in source_tags if t.startswith('/')]
        trans_open = [t for t in trans_tags if not t.startswith('/')]
        trans_close = [t[1:] for t in trans_tags if t.startswith('/')]

        for tag in set(source_open):
            sc = source_open.count(tag)
            tc = trans_open.count(tag)
            if sc != tc:
                issues.append(f"Opening tag <{tag}>: source={sc}, translation={tc}")

        for tag in set(source_close):
            sc = source_close.count(tag)
            tc = trans_close.count(tag)
            if sc != tc:
                issues.append(f"Closing tag </{tag}>: source={sc}, translation={tc}")

        return issues

    @staticmethod
    def check_placeholders(source: str, translation: str) -> List[str]:
        """Check that placeholders are preserved."""
        issues = []
        
        # {0}, {1}, etc.
        source_nums = set(re.findall(r'\{\d+\}', source))
        trans_nums = set(re.findall(r'\{\d+\}', translation))
        missing = source_nums - trans_nums
        if missing:
            issues.append(f"Missing numbered placeholders: {missing}")

        # {{variable}} format
        source_vars = set(re.findall(r'\{\{\w+\}\}', source))
        trans_vars = set(re.findall(r'\{\{\w+\}\}', translation))
        missing = source_vars - trans_vars
        if missing:
            issues.append(f"Missing variable placeholders: {missing}")

        return issues

    @staticmethod
    def check_dice_rolls(source: str, translation: str) -> List[str]:
        """Check that dice roll expressions are preserved."""
        issues = []
        source_rolls = set(re.findall(r'\[\[/r[^\]]+\]\]', source))
        trans_rolls = set(re.findall(r'\[\[/r[^\]]+\]\]', translation))
        missing = source_rolls - trans_rolls
        if missing:
            issues.append(f"Missing dice rolls: {missing}")
        return issues

    def validate(
        self,
        source: str,
        translation: str,
        entry_name: str = "",
        field: str = "",
    ) -> Dict:
        """Run all validation checks on a translation.

        Returns a dict with:
        - passed: bool
        - issues: list of issue strings
        - warnings: list of warning strings
        - link_count: (uuid_count, compendium_count) comparison
        """
        issues = []
        warnings = []

        # Link count check
        src_links = self.count_links(source)
        trans_links = self.count_links(translation)
        if src_links != trans_links:
            issues.append(
                f"Link count mismatch: source={src_links}, translation={trans_links}"
            )

        # HTML tag check
        tag_issues = self.check_html_tags(source, translation)
        issues.extend(tag_issues)

        # Placeholder check
        ph_issues = self.check_placeholders(source, translation)
        issues.extend(ph_issues)

        # Dice roll check
        roll_issues = self.check_dice_rolls(source, translation)
        issues.extend(roll_issues)

        # Length sanity check
        if translation and len(translation) < len(source) * 0.1:
            warnings.append(
                f"Translation significantly shorter than source "
                f"({len(translation)} vs {len(source)} chars)"
            )

        return {
            "passed": len(issues) == 0,
            "entry": entry_name,
            "field": field,
            "issues": issues,
            "warnings": warnings,
            "source_links": src_links,
            "trans_links": trans_links,
        }
