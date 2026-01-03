"""
Babele Converter Module

Python implementation of Babele converter logic for testing and validation.
This module mirrors the JavaScript implementation in babele.js for property-based testing.

Implements:
- Requirement 4.1: Embedded Items translation reuse
- Requirement 4.2: Shared abilities translation reuse
- Requirement 4.4: Nested content recursive translation
- Requirement 4.5: JournalEntry multi-page handling
"""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
import copy


@dataclass
class TranslationCache:
    """Cache for translated items to enable reuse across compendiums."""
    _cache: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def get(self, item_type: str, item_name: str) -> Optional[Dict[str, Any]]:
        """Get cached translation for an item."""
        cache_key = f"{item_type}:{item_name}"
        return self._cache.get(cache_key)
    
    def set(self, item_type: str, item_name: str, translation: Dict[str, Any]) -> None:
        """Cache a translation for an item."""
        cache_key = f"{item_type}:{item_name}"
        self._cache[cache_key] = translation
    
    def clear(self) -> None:
        """Clear all cached translations."""
        self._cache.clear()
    
    def has(self, item_type: str, item_name: str) -> bool:
        """Check if a translation is cached."""
        cache_key = f"{item_type}:{item_name}"
        return cache_key in self._cache


# Global translation cache instance
_translation_cache = TranslationCache()


def safe_merge(original: Dict[str, Any], translation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Safely merge translation into original object.
    
    Args:
        original: Original object
        translation: Translation object to merge
        
    Returns:
        Merged object (new copy, original unchanged)
    """
    if not original:
        return translation or {}
    if not translation:
        return copy.deepcopy(original)
    
    result = copy.deepcopy(original)
    
    for key, value in translation.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dicts
            result[key] = safe_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    
    return result


def find_translation_from_packs(
    item_name: str,
    item_type: str,
    packs: List[Dict[str, Any]],
    exclude_pack: Optional[Dict[str, Any]] = None,
    cache: Optional[TranslationCache] = None
) -> Optional[Dict[str, Any]]:
    """
    Find translation for an item from any translated compendium pack.
    
    Implements Requirements 4.1, 4.2 - Reuse translations from compendiums.
    
    Args:
        item_name: Name of the item to find translation for
        item_type: Type of the item (edge, power, ability, etc.)
        packs: List of translation packs to search
        exclude_pack: Pack to exclude from search (to avoid self-reference)
        cache: Optional translation cache
        
    Returns:
        Translation object or None if not found
    """
    if cache is None:
        cache = _translation_cache
    
    # Check cache first
    cached = cache.get(item_type, item_name)
    if cached is not None:
        return cached
    
    # Search through all packs
    for pack in packs:
        # Skip excluded pack and untranslated packs
        if pack is exclude_pack:
            continue
        if not pack.get('translated', False):
            continue
        
        translations = pack.get('translations', {})
        if item_name in translations:
            translation = translations[item_name]
            # Cache the result
            cache.set(item_type, item_name, translation)
            return translation
    
    return None


def translate_embedded_items(
    items: List[Dict[str, Any]],
    translations: Optional[Dict[str, Any]] = None,
    packs: Optional[List[Dict[str, Any]]] = None,
    current_pack: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Translate embedded items within an actor or other container.
    
    Implements Requirements 4.1, 4.2 - Reuse translations from compendiums.
    
    Args:
        items: Array of embedded items
        translations: Direct translations for these items (by ID or name)
        packs: List of translation packs for reuse lookup
        current_pack: Current pack to exclude from reuse search
        
    Returns:
        List of translated items
    """
    if not items:
        return []
    
    if not isinstance(items, list):
        return items
    
    result = []
    translations = translations or {}
    packs = packs or []
    
    for item in items:
        if not isinstance(item, dict):
            result.append(item)
            continue
        
        item_id = item.get('_id') or item.get('id')
        item_name = item.get('name', '')
        item_type = item.get('type', '')
        
        translated_item = None
        
        # Priority 1: Check for direct translation by ID
        if item_id and item_id in translations:
            translated_item = safe_merge(item, translations[item_id])
        
        # Priority 2: Check for direct translation by name
        elif item_name and item_name in translations:
            translated_item = safe_merge(item, translations[item_name])
        
        # Priority 3: Search in other translated compendiums for reuse
        elif packs:
            pack_translation = find_translation_from_packs(
                item_name, item_type, packs, current_pack
            )
            if pack_translation:
                translated_item = safe_merge(item, pack_translation)
                translated_item['_translationSource'] = 'compendium-reuse'
        
        result.append(translated_item if translated_item else copy.deepcopy(item))
    
    return result


def translate_nested_content(
    obj: Any,
    translations: Optional[Dict[str, Any]] = None,
    translatable_fields: Optional[List[str]] = None,
    depth: int = 0,
    max_depth: int = 10
) -> Any:
    """
    Recursively translate nested content within an object.
    
    Implements Requirement 4.4 - Recursive translation of nested fields.
    
    Args:
        obj: Object to translate
        translations: Translations for this object
        translatable_fields: List of field names that should be translated
        depth: Current recursion depth
        max_depth: Maximum recursion depth (default 10)
        
    Returns:
        Translated object (new copy, original unchanged)
    """
    if translatable_fields is None:
        translatable_fields = ['name', 'description', 'text', 'notes', 'biography']
    
    # Base cases
    if obj is None or depth > max_depth:
        return obj
    
    if not isinstance(obj, (dict, list)):
        return obj
    
    # Handle lists
    if isinstance(obj, list):
        return [
            translate_nested_content(item, None, translatable_fields, depth + 1, max_depth)
            for item in obj
        ]
    
    # Handle dicts
    result = {}
    translations = translations or {}
    
    for key, value in obj.items():
        # Check if this field has a direct translation
        if key in translations:
            trans_value = translations[key]
            if isinstance(trans_value, dict) and isinstance(value, dict):
                # Recursively translate nested objects
                result[key] = translate_nested_content(
                    value, trans_value, translatable_fields, depth + 1, max_depth
                )
            else:
                result[key] = copy.deepcopy(trans_value)
        elif isinstance(value, dict):
            # Recursively process nested objects even without direct translation
            result[key] = translate_nested_content(
                value, None, translatable_fields, depth + 1, max_depth
            )
        elif isinstance(value, list):
            # Process lists
            result[key] = translate_nested_content(
                value, None, translatable_fields, depth + 1, max_depth
            )
        else:
            result[key] = copy.deepcopy(value) if isinstance(value, (dict, list)) else value
    
    return result


def translate_journal_pages(
    pages: List[Dict[str, Any]],
    translations: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Translate JournalEntry pages.
    
    Implements Requirement 4.5 - Multi-page journal handling.
    
    Args:
        pages: Array of journal pages
        translations: Translations object (keyed by page ID or name)
        
    Returns:
        List of translated pages
    """
    if not pages:
        return []
    
    if not isinstance(pages, list):
        return pages
    
    translations = translations or {}
    result = []
    
    for page in pages:
        if not isinstance(page, dict):
            result.append(page)
            continue
        
        page_id = page.get('_id', '')
        page_name = page.get('name', '')
        
        # Try to find translation by ID first, then by name
        translation = translations.get(page_id) or translations.get(page_name)
        
        if not translation:
            result.append(copy.deepcopy(page))
            continue
        
        # Build the translated page object
        translated_page = copy.deepcopy(page)
        translated_page['translated'] = True
        
        # Apply name translation
        if 'name' in translation:
            translated_page['name'] = translation['name']
        
        # Handle image caption if present
        if 'caption' in translation or (page.get('image') and 'caption' in page.get('image', {})):
            if 'image' not in translated_page:
                translated_page['image'] = {}
            translated_page['image']['caption'] = translation.get(
                'caption', 
                page.get('image', {}).get('caption', '')
            )
        
        # Handle source URL if present
        if 'src' in translation:
            translated_page['src'] = translation['src']
        
        # Handle text content - support both direct text and nested text.content
        if 'text' in translation:
            if isinstance(page.get('text'), dict):
                translated_page['text'] = {
                    **page.get('text', {}),
                    'content': translation['text']
                }
            else:
                translated_page['text'] = translation['text']
        
        result.append(translated_page)
    
    return result


def translate_actions(
    actions: Dict[str, Any],
    translations: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Translate action names and descriptions.
    
    Args:
        actions: Actions object with skill and additional actions
        translations: Translations for actions
        
    Returns:
        Translated actions object
    """
    if not actions or not isinstance(actions, dict):
        return actions
    
    if not translations:
        return copy.deepcopy(actions)
    
    result = copy.deepcopy(actions)
    
    # Translate skill name
    if 'skill' in translations:
        result['skill'] = translations['skill']
    
    # Translate additional actions
    if 'additional' in actions and 'additional' in translations:
        result['additional'] = {}
        for key, action in actions.get('additional', {}).items():
            action_translation = translations.get('additional', {}).get(key)
            if action_translation:
                result['additional'][key] = safe_merge(action, action_translation)
            else:
                result['additional'][key] = copy.deepcopy(action)
    
    return result


def get_all_translatable_fields(obj: Dict[str, Any], path: str = "") -> List[str]:
    """
    Get all paths to translatable fields in an object.
    
    Useful for testing to verify all fields are being translated.
    
    Args:
        obj: Object to analyze
        path: Current path prefix
        
    Returns:
        List of dot-separated paths to translatable fields
    """
    translatable = ['name', 'description', 'text', 'notes', 'biography', 'caption']
    paths = []
    
    if not isinstance(obj, dict):
        return paths
    
    for key, value in obj.items():
        current_path = f"{path}.{key}" if path else key
        
        if key in translatable and isinstance(value, str):
            paths.append(current_path)
        elif isinstance(value, dict):
            paths.extend(get_all_translatable_fields(value, current_path))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    paths.extend(get_all_translatable_fields(item, f"{current_path}[{i}]"))
    
    return paths


def validate_translation_completeness(
    source: Dict[str, Any],
    translated: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate that all translatable fields have been translated.
    
    Args:
        source: Original source object
        translated: Translated object
        
    Returns:
        Dict with 'complete' bool and 'missing' list of untranslated paths
    """
    source_fields = set(get_all_translatable_fields(source))
    translated_fields = set(get_all_translatable_fields(translated))
    
    # Check which fields are still in English (same as source)
    missing = []
    for field_path in source_fields:
        # Get values at path
        source_value = _get_nested_value(source, field_path)
        translated_value = _get_nested_value(translated, field_path)
        
        if source_value == translated_value and source_value:
            missing.append(field_path)
    
    return {
        'complete': len(missing) == 0,
        'missing': missing,
        'total_fields': len(source_fields),
        'translated_fields': len(source_fields) - len(missing)
    }


def _get_nested_value(obj: Dict[str, Any], path: str) -> Any:
    """Get a value from a nested dict using dot notation with array support."""
    parts = path.replace('[', '.').replace(']', '').split('.')
    current = obj
    
    for part in parts:
        if not part:
            continue
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
        
        if current is None:
            return None
    
    return current
