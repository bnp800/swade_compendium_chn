"""Babele Converter 属性测试

Property 11: Nested Content Translation
Property 12: Multi-Page Journal Translation
Validates: Requirements 4.4, 4.5
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import copy

from automation.babele_converter import (
    translate_nested_content,
    translate_embedded_items,
    translate_journal_pages,
    find_translation_from_packs,
    TranslationCache,
)
from automation.babele_converter.converter import (
    safe_merge,
    translate_actions,
    get_all_translatable_fields,
    validate_translation_completeness,
)


# Strategies for generating test data

# Strategy for generating simple text content
text_strategy = st.text(min_size=1, max_size=100, alphabet=st.characters(
    whitelist_categories=('L', 'N', 'P', 'S', 'Zs'),
    whitelist_characters=' '
))

# Strategy for generating item IDs
id_strategy = st.text(min_size=16, max_size=16, alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')

# Strategy for generating item names
name_strategy = st.text(min_size=1, max_size=50, alphabet=st.characters(
    whitelist_categories=('L', 'N', 'P', 'S'),
    whitelist_characters=' '
))

# Strategy for generating HTML-like content
html_content_strategy = st.builds(
    lambda text: f"<p>{text}</p>",
    text_strategy
)

# Strategy for generating a simple item
simple_item_strategy = st.fixed_dictionaries({
    "_id": id_strategy,
    "name": name_strategy,
    "type": st.sampled_from(["edge", "hindrance", "power", "ability", "gear"]),
    "description": html_content_strategy,
})

# Strategy for generating nested content (up to 3 levels deep)
@st.composite
def nested_content_strategy(draw, max_depth=3, current_depth=0):
    """Generate nested content structures for testing."""
    if current_depth >= max_depth:
        return draw(st.one_of(text_strategy, st.integers(), st.booleans()))
    
    return draw(st.one_of(
        text_strategy,
        st.integers(),
        st.booleans(),
        st.dictionaries(
            keys=st.sampled_from(['name', 'description', 'text', 'notes', 'value', 'data', 'nested']),
            values=st.deferred(lambda: nested_content_strategy(max_depth, current_depth + 1)),
            min_size=1,
            max_size=5
        ),
        st.lists(
            st.deferred(lambda: nested_content_strategy(max_depth, current_depth + 1)),
            min_size=0,
            max_size=3
        )
    ))

# Strategy for generating journal pages
journal_page_strategy = st.fixed_dictionaries({
    "_id": id_strategy,
    "name": name_strategy,
    "text": st.one_of(
        html_content_strategy,
        st.fixed_dictionaries({
            "content": html_content_strategy,
            "format": st.just(1)
        })
    ),
}).map(lambda d: {**d, "type": "text"})

# Strategy for generating translation packs
translation_pack_strategy = st.fixed_dictionaries({
    "translated": st.booleans(),
    "translations": st.dictionaries(
        keys=name_strategy,
        values=st.fixed_dictionaries({
            "name": name_strategy,
            "description": html_content_strategy,
        }),
        min_size=0,
        max_size=10
    )
})


class TestNestedContentTranslation:
    """嵌套内容翻译属性测试
    
    Property 11: Nested Content Translation
    Validates: Requirements 4.4
    """
    
    @given(
        obj=st.fixed_dictionaries({
            "name": name_strategy,
            "description": html_content_strategy,
            "nested": st.fixed_dictionaries({
                "name": name_strategy,
                "text": html_content_strategy,
                "deeper": st.fixed_dictionaries({
                    "name": name_strategy,
                    "notes": html_content_strategy,
                })
            })
        }),
        translations=st.fixed_dictionaries({
            "name": name_strategy,
            "description": html_content_strategy,
            "nested": st.fixed_dictionaries({
                "name": name_strategy,
                "text": html_content_strategy,
                "deeper": st.fixed_dictionaries({
                    "name": name_strategy,
                    "notes": html_content_strategy,
                })
            })
        })
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_nested_content_translation_recursive(self, obj, translations):
        """
        Property 11: Nested Content Translation
        
        *For any* JSON structure with nested translatable fields (e.g., Actor with 
        embedded Items), the system SHALL recursively process all levels and 
        translate each translatable field.
        
        Feature: translation-automation-workflow, Property 11: Nested Content Translation
        **Validates: Requirements 4.4**
        """
        result = translate_nested_content(obj, translations)
        
        # Verify top-level fields are translated
        assert result["name"] == translations["name"], \
            "Top-level name should be translated"
        assert result["description"] == translations["description"], \
            "Top-level description should be translated"
        
        # Verify nested fields are translated
        assert result["nested"]["name"] == translations["nested"]["name"], \
            "Nested name should be translated"
        assert result["nested"]["text"] == translations["nested"]["text"], \
            "Nested text should be translated"
        
        # Verify deeply nested fields are translated
        assert result["nested"]["deeper"]["name"] == translations["nested"]["deeper"]["name"], \
            "Deeply nested name should be translated"
        assert result["nested"]["deeper"]["notes"] == translations["nested"]["deeper"]["notes"], \
            "Deeply nested notes should be translated"
    
    @given(obj=st.fixed_dictionaries({
        "name": name_strategy,
        "description": html_content_strategy,
        "untranslatable": st.integers(),
        "nested": st.fixed_dictionaries({
            "name": name_strategy,
            "value": st.integers(),
        })
    }))
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_nested_content_preserves_untranslated_fields(self, obj):
        """
        Property: Untranslated fields should be preserved unchanged.
        
        Feature: translation-automation-workflow, Property: Field preservation
        **Validates: Requirements 4.4**
        """
        # Only translate name fields
        translations = {
            "name": "翻译后的名称",
            "nested": {
                "name": "嵌套翻译名称"
            }
        }
        
        result = translate_nested_content(obj, translations)
        
        # Translated fields should be updated
        assert result["name"] == translations["name"]
        assert result["nested"]["name"] == translations["nested"]["name"]
        
        # Untranslated fields should be preserved
        assert result["description"] == obj["description"], \
            "Untranslated description should be preserved"
        assert result["untranslatable"] == obj["untranslatable"], \
            "Non-translatable fields should be preserved"
        assert result["nested"]["value"] == obj["nested"]["value"], \
            "Nested non-translatable fields should be preserved"
    
    @given(obj=st.fixed_dictionaries({
        "name": name_strategy,
        "items": st.lists(
            st.fixed_dictionaries({
                "name": name_strategy,
                "description": html_content_strategy,
            }),
            min_size=1,
            max_size=5
        )
    }))
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_nested_content_handles_arrays(self, obj):
        """
        Property: Arrays of nested objects should be processed correctly.
        
        Feature: translation-automation-workflow, Property: Array handling
        **Validates: Requirements 4.4**
        """
        result = translate_nested_content(obj, None)
        
        # Arrays should be preserved
        assert len(result["items"]) == len(obj["items"]), \
            "Array length should be preserved"
        
        # Each item should be a copy (not the same reference)
        for i, item in enumerate(result["items"]):
            assert item["name"] == obj["items"][i]["name"]
            assert item["description"] == obj["items"][i]["description"]
    
    @given(obj=st.fixed_dictionaries({
        "name": name_strategy,
        "description": html_content_strategy,
    }))
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_nested_content_does_not_modify_original(self, obj):
        """
        Property: Original object should not be modified.
        
        Feature: translation-automation-workflow, Property: Immutability
        **Validates: Requirements 4.4**
        """
        original = copy.deepcopy(obj)
        translations = {
            "name": "翻译后的名称",
            "description": "翻译后的描述"
        }
        
        result = translate_nested_content(obj, translations)
        
        # Original should be unchanged
        assert obj == original, "Original object should not be modified"
        
        # Result should be different
        assert result["name"] == translations["name"]
        assert result["description"] == translations["description"]
    
    @given(depth=st.integers(min_value=1, max_value=15))
    @settings(max_examples=50, deadline=5000)
    @pytest.mark.property
    def test_nested_content_respects_max_depth(self, depth):
        """
        Property: Recursion should stop at max depth to prevent stack overflow.
        
        Feature: translation-automation-workflow, Property: Depth limit
        **Validates: Requirements 4.4**
        """
        # Create deeply nested structure
        obj = {"name": "root"}
        current = obj
        for i in range(depth):
            current["nested"] = {"name": f"level_{i}"}
            current = current["nested"]
        
        # Should not raise RecursionError
        result = translate_nested_content(obj, None, max_depth=10)
        
        # Result should exist
        assert result is not None
        assert result["name"] == "root"


class TestMultiPageJournalTranslation:
    """多页面日志翻译属性测试
    
    Property 12: Multi-Page Journal Translation
    Validates: Requirements 4.5
    """
    
    @given(
        pages=st.lists(journal_page_strategy, min_size=1, max_size=10, unique_by=lambda p: p["_id"])
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_multi_page_journal_translation(self, pages):
        """
        Property 12: Multi-Page Journal Translation
        
        *For any* JournalEntry with multiple pages, each page SHALL be translated 
        independently while maintaining the page structure and order.
        
        Feature: translation-automation-workflow, Property 12: Multi-Page Journal Translation
        **Validates: Requirements 4.5**
        """
        # Create translations for each page
        translations = {}
        for page in pages:
            translations[page["_id"]] = {
                "name": f"翻译_{page['name']}",
                "text": f"<p>翻译内容 for {page['name']}</p>"
            }
        
        result = translate_journal_pages(pages, translations)
        
        # Verify page count is preserved
        assert len(result) == len(pages), \
            "Number of pages should be preserved"
        
        # Verify page order is preserved
        for i, (original, translated) in enumerate(zip(pages, result)):
            assert translated["_id"] == original["_id"], \
                f"Page {i} ID should be preserved"
        
        # Verify each page is translated
        for i, translated in enumerate(result):
            page_id = translated["_id"]
            expected_translation = translations[page_id]
            
            assert translated["name"] == expected_translation["name"], \
                f"Page {i} name should be translated"
            assert translated.get("translated") is True, \
                f"Page {i} should be marked as translated"
    
    @given(
        pages=st.lists(journal_page_strategy, min_size=2, max_size=5, unique_by=lambda p: p["_id"])
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_multi_page_partial_translation(self, pages):
        """
        Property: Pages without translations should be preserved unchanged.
        
        Feature: translation-automation-workflow, Property: Partial translation
        **Validates: Requirements 4.5**
        """
        # Only translate first page by its ID (not by name to avoid collision)
        translations = {}
        if pages:
            first_page = pages[0]
            translations[first_page["_id"]] = {
                "name": "翻译后的第一页",
                "text": "<p>翻译内容</p>"
            }
        
        result = translate_journal_pages(pages, translations)
        
        # First page should be translated
        if pages:
            assert result[0]["name"] == "翻译后的第一页"
            assert result[0].get("translated") is True
        
        # Other pages should be unchanged (check by ID to ensure we're comparing the right pages)
        for i in range(1, len(pages)):
            # Skip if this page's name happens to match the first page's ID
            if pages[i]["name"] == pages[0]["_id"]:
                continue
            # Skip if this page's ID is in translations
            if pages[i]["_id"] in translations:
                continue
            assert result[i]["name"] == pages[i]["name"], \
                f"Untranslated page {i} name should be preserved"
            assert result[i].get("translated") is not True, \
                f"Untranslated page {i} should not be marked as translated"
    
    @given(pages=st.lists(journal_page_strategy, min_size=0, max_size=5))
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_multi_page_empty_translations(self, pages):
        """
        Property: Empty or None translations should preserve all pages.
        
        Feature: translation-automation-workflow, Property: Empty translation handling
        **Validates: Requirements 4.5**
        """
        result_none = translate_journal_pages(pages, None)
        result_empty = translate_journal_pages(pages, {})
        
        # Both should preserve all pages
        assert len(result_none) == len(pages)
        assert len(result_empty) == len(pages)
        
        # Content should be preserved
        for i, page in enumerate(pages):
            assert result_none[i]["name"] == page["name"]
            assert result_empty[i]["name"] == page["name"]
    
    @given(
        pages=st.lists(journal_page_strategy, min_size=1, max_size=5, unique_by=lambda p: p["_id"])
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_multi_page_translation_by_name(self, pages):
        """
        Property: Pages can be translated by name if ID is not found.
        
        Feature: translation-automation-workflow, Property: Name-based lookup
        **Validates: Requirements 4.5**
        """
        # Create translations keyed by name with a unique prefix to avoid ID collision
        translations = {}
        for page in pages:
            translations[f"PAGE_{page['name']}"] = {
                "name": f"按名称翻译_{page['name']}",
                "text": "<p>按名称翻译的内容</p>"
            }
        
        # Modify pages to have names that match our translation keys
        modified_pages = []
        for page in pages:
            modified_page = {**page, "name": f"PAGE_{page['name']}"}
            modified_pages.append(modified_page)
        
        result = translate_journal_pages(modified_pages, translations)
        
        # Each page should be translated
        for i, translated in enumerate(result):
            original_name = pages[i]["name"]
            expected_name = f"按名称翻译_{original_name}"
            
            assert translated["name"] == expected_name, \
                f"Page {i} should be translated by name lookup"
    
    @given(pages=st.lists(journal_page_strategy, min_size=1, max_size=5))
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_multi_page_does_not_modify_original(self, pages):
        """
        Property: Original pages array should not be modified.
        
        Feature: translation-automation-workflow, Property: Immutability
        **Validates: Requirements 4.5**
        """
        original = copy.deepcopy(pages)
        translations = {
            pages[0]["_id"]: {"name": "翻译名称", "text": "翻译内容"}
        } if pages else {}
        
        result = translate_journal_pages(pages, translations)
        
        # Original should be unchanged
        assert pages == original, "Original pages should not be modified"
        
        # Result should be different (if translations were applied)
        if pages and translations:
            assert result[0]["name"] != pages[0]["name"]


class TestEmbeddedItemsTranslation:
    """嵌入物品翻译属性测试"""
    
    @given(
        items=st.lists(simple_item_strategy, min_size=1, max_size=10, unique_by=lambda i: i["_id"])
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_embedded_items_translation_by_id(self, items):
        """
        Property: Items should be translated by ID first.
        
        Feature: translation-automation-workflow, Property: ID-based translation
        **Validates: Requirements 4.1, 4.2**
        """
        # Create translations keyed by ID
        translations = {}
        for item in items:
            translations[item["_id"]] = {
                "name": f"翻译_{item['name']}",
                "description": f"<p>翻译描述 for {item['name']}</p>"
            }
        
        result = translate_embedded_items(items, translations)
        
        # Each item should be translated
        for i, translated in enumerate(result):
            item_id = items[i]["_id"]
            expected = translations[item_id]
            
            assert translated["name"] == expected["name"], \
                f"Item {i} name should be translated"
            assert translated["description"] == expected["description"], \
                f"Item {i} description should be translated"
    
    @given(
        items=st.lists(simple_item_strategy, min_size=1, max_size=5, unique_by=lambda i: i["_id"])
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_embedded_items_translation_by_name(self, items):
        """
        Property: Items should be translated by name if ID not found in translations.
        
        Feature: translation-automation-workflow, Property: Name-based translation
        **Validates: Requirements 4.1, 4.2**
        """
        # Create translations keyed by name with a unique prefix to avoid ID collision
        # This tests the fallback to name-based lookup when ID is not in translations
        translations = {}
        for item in items:
            # Use a prefix that won't match any generated ID
            translations[f"NAME_{item['name']}"] = {
                "name": f"按名称翻译_{item['name']}",
                "description": "<p>按名称翻译的描述</p>"
            }
        
        # Modify items to have names that match our translation keys
        modified_items = []
        for item in items:
            modified_item = {**item, "name": f"NAME_{item['name']}"}
            modified_items.append(modified_item)
        
        result = translate_embedded_items(modified_items, translations)
        
        # Each item should be translated by name since IDs are not in translations
        for i, translated in enumerate(result):
            original_name = items[i]["name"]
            expected_name = f"按名称翻译_{original_name}"
            
            assert translated["name"] == expected_name, \
                f"Item {i} should be translated by name lookup"
    
    @given(
        items=st.lists(simple_item_strategy, min_size=1, max_size=5),
        packs=st.lists(translation_pack_strategy, min_size=1, max_size=3)
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_embedded_items_reuse_from_packs(self, items, packs):
        """
        Property: Items should be translated from other packs if not in direct translations.
        
        Feature: translation-automation-workflow, Property: Pack reuse
        **Validates: Requirements 4.1, 4.2**
        """
        # Ensure at least one pack is translated and has matching translations
        if packs:
            packs[0]["translated"] = True
            for item in items[:2]:  # Add translations for first 2 items
                packs[0]["translations"][item["name"]] = {
                    "name": f"从包复用_{item['name']}",
                    "description": "<p>从包复用的描述</p>"
                }
        
        # No direct translations
        result = translate_embedded_items(items, {}, packs)
        
        # Items with pack translations should be translated
        for i, translated in enumerate(result):
            original_name = items[i]["name"]
            if original_name in packs[0]["translations"]:
                assert translated["name"] == f"从包复用_{original_name}", \
                    f"Item {i} should be translated from pack"
                assert translated.get("_translationSource") == "compendium-reuse", \
                    f"Item {i} should be marked as compendium-reuse"


class TestTranslationCache:
    """翻译缓存测试"""
    
    @given(
        item_type=st.sampled_from(["edge", "power", "ability"]),
        item_name=name_strategy,
        translation=st.fixed_dictionaries({
            "name": name_strategy,
            "description": html_content_strategy,
        })
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_cache_set_and_get(self, item_type, item_name, translation):
        """
        Property: Cached translations should be retrievable.
        
        Feature: translation-automation-workflow, Property: Cache functionality
        **Validates: Requirements 4.1, 4.2**
        """
        cache = TranslationCache()
        
        # Initially not in cache
        assert cache.get(item_type, item_name) is None
        assert not cache.has(item_type, item_name)
        
        # Set and retrieve
        cache.set(item_type, item_name, translation)
        
        assert cache.has(item_type, item_name)
        assert cache.get(item_type, item_name) == translation
    
    @given(
        items=st.lists(
            st.tuples(
                st.sampled_from(["edge", "power", "ability"]),
                name_strategy,
                st.fixed_dictionaries({"name": name_strategy})
            ),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_cache_clear(self, items):
        """
        Property: Cache clear should remove all entries.
        
        Feature: translation-automation-workflow, Property: Cache clear
        **Validates: Requirements 4.1, 4.2**
        """
        cache = TranslationCache()
        
        # Add items to cache
        for item_type, item_name, translation in items:
            cache.set(item_type, item_name, translation)
        
        # Clear cache
        cache.clear()
        
        # All items should be gone
        for item_type, item_name, _ in items:
            assert not cache.has(item_type, item_name)
            assert cache.get(item_type, item_name) is None


class TestSafeMerge:
    """安全合并测试"""
    
    @given(
        original=st.fixed_dictionaries({
            "name": name_strategy,
            "value": st.integers(),
        }),
        translation=st.fixed_dictionaries({
            "name": name_strategy,
        })
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_safe_merge_preserves_unmerged_fields(self, original, translation):
        """
        Property: Fields not in translation should be preserved.
        
        Feature: translation-automation-workflow, Property: Merge preservation
        **Validates: Requirements 4.1, 4.2**
        """
        result = safe_merge(original, translation)
        
        # Translation field should be applied
        assert result["name"] == translation["name"]
        
        # Original-only field should be preserved
        assert result["value"] == original["value"]
    
    @given(
        original=st.fixed_dictionaries({
            "name": name_strategy,
            "nested": st.fixed_dictionaries({
                "a": st.integers(),
                "b": st.integers(),
            })
        }),
        translation=st.fixed_dictionaries({
            "nested": st.fixed_dictionaries({
                "a": st.integers(),
            })
        })
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_safe_merge_recursive(self, original, translation):
        """
        Property: Nested objects should be merged recursively.
        
        Feature: translation-automation-workflow, Property: Recursive merge
        **Validates: Requirements 4.1, 4.2**
        """
        result = safe_merge(original, translation)
        
        # Nested translation should be applied
        assert result["nested"]["a"] == translation["nested"]["a"]
        
        # Nested original-only field should be preserved
        assert result["nested"]["b"] == original["nested"]["b"]
        
        # Top-level original field should be preserved
        assert result["name"] == original["name"]
