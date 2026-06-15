"""Core translation engine for SWADE compendium JSON files.

Translates every translatable field in every entry, handling:
- Simple text fields (name, category)
- HTML-rich fields (description, text, biography)
- Nested structures (pages, items, abilities)
- Actions with skill/additional action names
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from .client import DeepSeekClient, create_client_from_env
from .chunker import chunk_html, merge_chunks
from .prompts import PromptBuilder, TranslationValidator

logger = logging.getLogger(__name__)


# Fields to translate for each entry type
TRANSLATABLE_FIELDS = [
    "name",
    "description",
    "text",
    "category",
    "biography",
    "notes",
    "appearance",
    "archetype",
    "goals",
    "trapping",
    "range",
    "duration",
    "caption",
    "tokenName",
    "species",
    "classification",
    "driverSkill",
    "label",
]

# Fields that contain HTML and should be chunked
HTML_FIELDS = {"description", "text", "biography", "notes"}

# Fields that are short labels (lower temperature)
SHORT_FIELDS = {"name", "category", "tokenName", "species", "label"}


class CompendiumTranslator:
    """Translates a single Babele-format compendium JSON file."""

    def __init__(
        self,
        client: DeepSeekClient,
        prompt_builder: PromptBuilder,
        validator: Optional[TranslationValidator] = None,
        max_chunk_size: int = 1800,
        dry_run: bool = False,
    ):
        self.client = client
        self.prompt_builder = prompt_builder
        self.validator = validator or TranslationValidator()
        self.max_chunk_size = max_chunk_size
        self.dry_run = dry_run
        self.stats = {
            "entries_processed": 0,
            "fields_translated": 0,
            "chunks_translated": 0,
            "validation_failures": 0,
        }

    def translate_entry(
        self,
        entry_name: str,
        entry_data: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], List[Dict]]:
        """Translate all translatable fields in a single entry.

        Args:
            entry_name: The entry key (English name).
            entry_data: The entry data dict with fields.

        Returns:
            (translated_entry, validation_results)
        """
        translated = dict(entry_data)
        validations = []

        for field in TRANSLATABLE_FIELDS:
            if field not in entry_data:
                continue
            
            value = entry_data[field]
            if not value or not isinstance(value, str):
                continue
            
            # Skip if value is empty or whitespace
            if not value.strip():
                continue

            # Determine field type for prompt hints
            field_type = "name" if field in SHORT_FIELDS else \
                         "category" if field == "category" else \
                         "description"

            if field in HTML_FIELDS and len(value) > self.max_chunk_size:
                # Chunk and translate
                translated_value = self._translate_html_field(
                    value, entry_name, field, field_type
                )
            else:
                # Direct translation
                translated_value = self._translate_text_field(
                    value, entry_name, field, field_type
                )

            if translated_value is not None and translated_value != value:
                translated[field] = translated_value
                self.stats["fields_translated"] += 1

                # Validate
                result = self.validator.validate(
                    value, translated_value, entry_name, field
                )
                if not result["passed"]:
                    self.stats["validation_failures"] += 1
                    logger.warning(
                        f"Validation issues in {entry_name}.{field}: "
                        f"{result['issues']}"
                    )
                validations.append(result)

        self.stats["entries_processed"] += 1
        return translated, validations

    def _translate_text_field(
        self,
        text: str,
        entry_name: str,
        field: str,
        field_type: str,
    ) -> Optional[str]:
        """Translate a simple text field (no chunking needed)."""
        prompt = self.prompt_builder.build(text, field_type)
        context = f"Entry: {entry_name}, Field: {field}"

        if self.dry_run:
            logger.info(f"[DRY RUN] Would translate {entry_name}.{field} "
                        f"({len(text)} chars)")
            return None

        temperature = 0.2 if field in SHORT_FIELDS else 0.3
        return self.client.translate(
            text=text,
            system_prompt=prompt,
            context=context,
            temperature=temperature,
        )

    def _translate_html_field(
        self,
        html_text: str,
        entry_name: str,
        field: str,
        field_type: str,
    ) -> Optional[str]:
        """Translate an HTML field with chunking."""
        chunks = chunk_html(html_text, self.max_chunk_size)
        
        if len(chunks) == 1:
            return self._translate_text_field(html_text, entry_name, field, field_type)

        logger.info(f"  Chunking {entry_name}.{field}: "
                    f"{len(html_text)} chars → {len(chunks)} chunks")

        translations = []
        for chunk in chunks:
            if self.dry_run:
                translations.append(None)
                continue

            context = f"Entry: {entry_name}, Field: {field}, Chunk {chunk.index+1}/{len(chunks)}"
            prompt = self.prompt_builder.build(chunk.text, field_type)
            
            translation = self.client.translate(
                text=chunk.text,
                system_prompt=prompt,
                context=context,
                temperature=0.3,
            )
            translations.append(translation)
            self.stats["chunks_translated"] += 1

        if None in translations:
            logger.error(f"  Failed to translate some chunks for {entry_name}.{field}")
            return None

        return merge_chunks(chunks, translations)

    def translate_pages(
        self,
        pages: Dict[str, Any],
        entry_name: str,
    ) -> Dict[str, Any]:
        """Translate JournalEntry pages."""
        translated_pages = {}
        for page_id, page_data in pages.items():
            translated_page = dict(page_data)
            
            # Translate page name
            if "name" in page_data and page_data["name"]:
                name_trans = self._translate_text_field(
                    page_data["name"], f"{entry_name}/{page_id}", "name", "name"
                )
                if name_trans:
                    translated_page["name"] = name_trans
            
            # Translate page text
            if "text" in page_data and page_data["text"]:
                text_trans = self._translate_html_field(
                    page_data["text"], f"{entry_name}/{page_id}", "text", "description"
                )
                if text_trans:
                    translated_page["text"] = text_trans
            
            # Translate image caption
            if "image" in page_data and isinstance(page_data["image"], dict):
                caption = page_data["image"].get("caption")
                if caption:
                    cap_trans = self._translate_text_field(
                        caption, f"{entry_name}/{page_id}", "caption", "description"
                    )
                    if cap_trans:
                        translated_page["image"] = {
                            **page_data["image"],
                            "caption": cap_trans,
                        }
            
            translated_pages[page_id] = translated_page
        
        return translated_pages

    def translate_actions(
        self,
        actions: Dict[str, Any],
        entry_name: str,
    ) -> Dict[str, Any]:
        """Translate actions structure (skill + additional actions)."""
        translated = dict(actions)
        
        if "skill" in actions and actions["skill"]:
            trans = self._translate_text_field(
                actions["skill"], f"{entry_name}/skill", "skill", "name"
            )
            if trans:
                translated["skill"] = trans

        if "additional" in actions:
            translated["additional"] = {}
            for key, action in actions.get("additional", {}).items():
                if isinstance(action, dict) and "name" in action:
                    trans = self._translate_text_field(
                        action["name"], f"{entry_name}/action/{key}", "action_name", "name"
                    )
                    if trans:
                        translated["additional"][key] = {**action, "name": trans}
                    else:
                        translated["additional"][key] = action
                else:
                    translated["additional"][key] = action

        return translated

    def translate_file(
        self,
        input_path: Path,
        output_path: Optional[Path] = None,
    ) -> Optional[Dict]:
        """Translate an entire compendium JSON file.

        Args:
            input_path: Path to en-US/*.json file.
            output_path: Path to write zh_Hans/*.json. If None, returns dict.

        Returns:
            The translated data dict, or None on failure.
        """
        logger.info(f"Translating: {input_path.name}")

        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        translated_data = {
            "label": data.get("label", ""),
            "entries": {},
        }
        
        # Preserve mapping and folders if present
        if "mapping" in data:
            translated_data["mapping"] = data["mapping"]
        if "folders" in data:
            translated_data["folders"] = data["folders"]

        entries = data.get("entries", {})
        total = len(entries)
        
        for i, (entry_name, entry_data) in enumerate(entries.items()):
            if (i + 1) % 20 == 0:
                logger.info(f"  Progress: {i+1}/{total}")

            # Handle entries with pages (JournalEntry)
            if "pages" in entry_data:
                translated_entry = self.translate_pages(
                    entry_data["pages"], entry_name
                )
                translated_data["entries"][entry_name] = {
                    **entry_data,
                    "pages": translated_entry,
                }
                self.stats["entries_processed"] += 1
                continue

            # Handle entries with items (Adventure)
            if "items" in entry_data:
                translated_items = {}
                for item_id, item_data in entry_data["items"].items():
                    item_trans, _ = self.translate_entry(item_id, item_data)
                    translated_items[item_id] = item_trans
                translated_data["entries"][entry_name] = {
                    **entry_data,
                    "items": translated_items,
                }
                self.stats["entries_processed"] += 1
                continue

            # Standard entry
            translated_entry, validations = self.translate_entry(
                entry_name, entry_data
            )

            # Handle actions if present
            if "actions" in translated_entry and translated_entry["actions"]:
                translated_entry["actions"] = self.translate_actions(
                    translated_entry["actions"], entry_name
                )

            translated_data["entries"][entry_name] = translated_entry

        logger.info(
            f"  Done: {self.stats['entries_processed']} entries, "
            f"{self.stats['fields_translated']} fields, "
            f"{self.stats['chunks_translated']} chunks, "
            f"{self.stats['validation_failures']} validation issues"
        )

        if output_path and not self.dry_run:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(translated_data, f, ensure_ascii=False, indent=2)
            logger.info(f"  Saved: {output_path}")

        return translated_data


def translate_directory(
    en_dir: Path,
    zh_dir: Path,
    glossary_path: Path,
    few_shot_path: Path,
    pattern: str = "*.json",
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Translate all compendium files in a directory.

    Returns summary stats.
    """
    client = create_client_from_env()
    prompt_builder = PromptBuilder(
        glossary_path=glossary_path,
        few_shot_path=few_shot_path,
        max_glossary_terms=80,
        max_few_shot=3,
    )
    translator = CompendiumTranslator(
        client=client,
        prompt_builder=prompt_builder,
        dry_run=dry_run,
    )

    summary = {"files_processed": 0, "total_entries": 0, "total_fields": 0}
    
    files = sorted(en_dir.glob(pattern))
    for en_file in files:
        # Skip placeholder
        if en_file.name == "___.json":
            continue

        zh_file = zh_dir / en_file.name
        
        result = translator.translate_file(en_file, zh_file)
        if result:
            summary["files_processed"] += 1
            summary["total_entries"] += len(result.get("entries", {}))
            summary["total_fields"] += translator.stats["fields_translated"]

    return summary
