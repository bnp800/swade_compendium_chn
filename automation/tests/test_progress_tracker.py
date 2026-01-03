"""Progress Tracker 属性测试

Property 7: Progress Calculation Accuracy
Validates: Requirements 5.1, 5.2

Property 6: Change Marking Accuracy
Validates: Requirements 5.3, 8.3
"""

import json
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, strategies as st, settings, assume

from automation.progress_tracker import ProgressTracker, ProgressReport, CompendiumProgress


# Strategy for generating entry content (simulating Babele JSON entry structure)
entry_content_strategy = st.fixed_dictionaries({
    "name": st.text(min_size=1, max_size=50),
    "description": st.text(min_size=0, max_size=200),
    "category": st.text(min_size=0, max_size=30),
})

# Strategy for generating entries dict
entries_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=('L', 'N', 'P', 'S'),
        whitelist_characters=' '
    )),
    values=entry_content_strategy,
    min_size=0,
    max_size=20
)

# Strategy for generating translated entry (different name from source)
def translated_entry_strategy(source_entry):
    """Generate a translated entry based on source entry"""
    return st.fixed_dictionaries({
        "name": st.text(min_size=1, max_size=50).filter(lambda x: x != source_entry.get("name", "")),
        "description": st.text(min_size=0, max_size=200),
        "category": st.text(min_size=0, max_size=30),
    })


class TestProgressCalculationAccuracy:
    """进度计算准确性属性测试
    
    Property 7: Progress Calculation Accuracy
    Validates: Requirements 5.1, 5.2
    """
    
    @given(source_entries=entries_strategy)
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_progress_calculation_accuracy(self, source_entries):
        """
        Property 7: Progress Calculation Accuracy
        
        *For any* pair of source and target directories, the calculated progress 
        percentage SHALL equal (translated_entries / total_entries * 100), where 
        an entry is considered translated if it has non-empty translated content.
        
        Feature: translation-automation-workflow, Property 7: Progress Calculation Accuracy
        **Validates: Requirements 5.1, 5.2**
        """
        tracker = ProgressTracker()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            source_dir = temp_dir / "en-US"
            target_dir = temp_dir / "zh_Hans"
            source_dir.mkdir(parents=True, exist_ok=True)
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Create source file
            source_file = source_dir / "test-compendium.json"
            with open(source_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": source_entries}, f, ensure_ascii=False, indent=2)
            
            # Create target file with some translated entries
            # Translate approximately half of the entries
            target_entries = {}
            translated_count = 0
            for i, (key, entry) in enumerate(source_entries.items()):
                if i % 2 == 0:
                    # Translate this entry (use different name)
                    target_entries[key] = {
                        "name": f"翻译_{entry['name']}" if entry.get('name') else "翻译名称",
                        "description": entry.get("description", ""),
                        "category": entry.get("category", "")
                    }
                    translated_count += 1
                # else: leave untranslated (not in target)
            
            target_file = target_dir / "test-compendium.json"
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": target_entries}, f, ensure_ascii=False, indent=2)
            
            # Calculate progress
            report = tracker.calculate_progress(str(source_dir), str(target_dir))
            
            total = len(source_entries)
            
            # Verify total entries
            assert report.total_entries == total, \
                f"Total entries mismatch: expected {total}, got {report.total_entries}"
            
            # Verify translated entries count
            assert report.translated_entries == translated_count, \
                f"Translated entries mismatch: expected {translated_count}, got {report.translated_entries}"
            
            # Verify untranslated entries count
            expected_untranslated = total - translated_count
            assert report.untranslated_entries == expected_untranslated, \
                f"Untranslated entries mismatch: expected {expected_untranslated}, got {report.untranslated_entries}"
            
            # Verify percentage calculation
            if total > 0:
                expected_percentage = (translated_count / total) * 100
                assert abs(report.completion_percentage - expected_percentage) < 0.001, \
                    f"Percentage mismatch: expected {expected_percentage}, got {report.completion_percentage}"
            else:
                assert report.completion_percentage == 0.0, \
                    "Empty source should have 0% completion"
    
    @given(entries=entries_strategy)
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_empty_target_yields_zero_progress(self, entries):
        """
        Property: When target directory has no translations, progress should be 0%.
        
        Feature: translation-automation-workflow, Property: Zero progress
        **Validates: Requirements 5.1, 5.2**
        """
        tracker = ProgressTracker()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            source_dir = temp_dir / "en-US"
            target_dir = temp_dir / "zh_Hans"
            source_dir.mkdir(parents=True, exist_ok=True)
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Create source file with entries
            source_file = source_dir / "test.json"
            with open(source_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": entries}, f, ensure_ascii=False, indent=2)
            
            # Create empty target file
            target_file = target_dir / "test.json"
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": {}}, f, ensure_ascii=False, indent=2)
            
            report = tracker.calculate_progress(str(source_dir), str(target_dir))
            
            if len(entries) > 0:
                assert report.translated_entries == 0, \
                    "Empty target should have 0 translated entries"
                assert report.completion_percentage == 0.0, \
                    "Empty target should have 0% completion"
                assert report.untranslated_entries == len(entries), \
                    "All entries should be untranslated"
    
    @given(entries=entries_strategy)
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_full_translation_yields_100_percent(self, entries):
        """
        Property: When all entries are translated, progress should be 100%.
        
        Feature: translation-automation-workflow, Property: Full progress
        **Validates: Requirements 5.1, 5.2**
        """
        assume(len(entries) > 0)  # Need at least one entry
        
        tracker = ProgressTracker()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            source_dir = temp_dir / "en-US"
            target_dir = temp_dir / "zh_Hans"
            source_dir.mkdir(parents=True, exist_ok=True)
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Create source file
            source_file = source_dir / "test.json"
            with open(source_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": entries}, f, ensure_ascii=False, indent=2)
            
            # Create fully translated target file
            target_entries = {}
            for key, entry in entries.items():
                target_entries[key] = {
                    "name": f"翻译_{entry['name']}" if entry.get('name') else "翻译名称",
                    "description": entry.get("description", ""),
                    "category": entry.get("category", "")
                }
            
            target_file = target_dir / "test.json"
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": target_entries}, f, ensure_ascii=False, indent=2)
            
            report = tracker.calculate_progress(str(source_dir), str(target_dir))
            
            assert report.translated_entries == len(entries), \
                f"All entries should be translated: expected {len(entries)}, got {report.translated_entries}"
            assert report.completion_percentage == 100.0, \
                f"Should have 100% completion: got {report.completion_percentage}"
            assert report.untranslated_entries == 0, \
                "Should have 0 untranslated entries"
    
    @given(
        entries1=entries_strategy,
        entries2=entries_strategy
    )
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_multiple_compendiums_aggregation(self, entries1, entries2):
        """
        Property: Progress across multiple compendiums should be correctly aggregated.
        
        Feature: translation-automation-workflow, Property: Aggregation
        **Validates: Requirements 5.1, 5.2**
        """
        tracker = ProgressTracker()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            source_dir = temp_dir / "en-US"
            target_dir = temp_dir / "zh_Hans"
            source_dir.mkdir(parents=True, exist_ok=True)
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Create first compendium (fully translated)
            source_file1 = source_dir / "compendium1.json"
            with open(source_file1, 'w', encoding='utf-8') as f:
                json.dump({"entries": entries1}, f, ensure_ascii=False, indent=2)
            
            target_entries1 = {
                key: {"name": f"翻译_{entry['name']}" if entry.get('name') else "翻译", 
                      "description": entry.get("description", "")}
                for key, entry in entries1.items()
            }
            target_file1 = target_dir / "compendium1.json"
            with open(target_file1, 'w', encoding='utf-8') as f:
                json.dump({"entries": target_entries1}, f, ensure_ascii=False, indent=2)
            
            # Create second compendium (not translated)
            source_file2 = source_dir / "compendium2.json"
            with open(source_file2, 'w', encoding='utf-8') as f:
                json.dump({"entries": entries2}, f, ensure_ascii=False, indent=2)
            
            target_file2 = target_dir / "compendium2.json"
            with open(target_file2, 'w', encoding='utf-8') as f:
                json.dump({"entries": {}}, f, ensure_ascii=False, indent=2)
            
            report = tracker.calculate_progress(str(source_dir), str(target_dir))
            
            total = len(entries1) + len(entries2)
            translated = len(entries1)
            
            assert report.total_entries == total, \
                f"Total should be sum of both compendiums: expected {total}, got {report.total_entries}"
            assert report.translated_entries == translated, \
                f"Translated should be from first compendium: expected {translated}, got {report.translated_entries}"
            
            # Verify by_compendium breakdown
            assert len(report.by_compendium) == 2, "Should have 2 compendiums"
            assert "compendium1" in report.by_compendium
            assert "compendium2" in report.by_compendium
    
    @given(entries=entries_strategy)
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_deprecated_entries_not_counted_as_translated(self, entries):
        """
        Property: Entries marked as deprecated should not be counted as translated.
        
        Feature: translation-automation-workflow, Property: Deprecated handling
        **Validates: Requirements 5.1, 5.2**
        """
        assume(len(entries) > 0)
        
        tracker = ProgressTracker()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            source_dir = temp_dir / "en-US"
            target_dir = temp_dir / "zh_Hans"
            source_dir.mkdir(parents=True, exist_ok=True)
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Create source file
            source_file = source_dir / "test.json"
            with open(source_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": entries}, f, ensure_ascii=False, indent=2)
            
            # Create target file with all entries marked as deprecated
            target_entries = {}
            for key, entry in entries.items():
                target_entries[key] = {
                    "name": f"翻译_{entry['name']}" if entry.get('name') else "翻译",
                    "description": entry.get("description", ""),
                    "_meta": {
                        "deprecated": True,
                        "deprecated_at": "2024-01-01T00:00:00"
                    }
                }
            
            target_file = target_dir / "test.json"
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": target_entries}, f, ensure_ascii=False, indent=2)
            
            report = tracker.calculate_progress(str(source_dir), str(target_dir))
            
            assert report.translated_entries == 0, \
                "Deprecated entries should not be counted as translated"
            assert report.untranslated_entries == len(entries), \
                "Deprecated entries should be counted as untranslated"



class TestChangeMarkingAccuracy:
    """变更标记准确性属性测试
    
    Property 6: Change Marking Accuracy
    Validates: Requirements 5.3, 8.3
    """
    
    @given(
        source_entries=entries_strategy,
        translation_entries=entries_strategy
    )
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_change_marking_accuracy(self, source_entries, translation_entries):
        """
        Property 6: Change Marking Accuracy
        
        *For any* source file update where entries are modified, the corresponding 
        translation entries SHALL be marked as "needs review" with the modification 
        timestamp.
        
        Feature: translation-automation-workflow, Property 6: Change Marking Accuracy
        **Validates: Requirements 5.3, 8.3**
        """
        tracker = ProgressTracker()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            
            # Create initial source entries with specific content
            initial_source = {}
            for key in source_entries.keys():
                initial_source[key] = {
                    "name": f"Original_{key}",
                    "description": "Original description",
                    "category": "Original"
                }
            
            # Create translation entries with source_hash recorded
            translated_entries = {}
            for key in source_entries.keys():
                source_hash = tracker._compute_content_hash(initial_source[key])
                translated_entries[key] = {
                    "name": f"翻译_{key}",
                    "description": "翻译描述",
                    "_meta": {
                        "source_hash": source_hash,
                        "translated_at": "2024-01-01T00:00:00"
                    }
                }
            
            # Now modify some source entries (simulate source update)
            modified_source = {}
            modified_keys = set()
            for i, (key, entry) in enumerate(initial_source.items()):
                if i % 2 == 0:
                    # Modify this entry
                    modified_source[key] = {
                        "name": f"Modified_{key}",
                        "description": "Modified description",
                        "category": "Modified"
                    }
                    modified_keys.add(key)
                else:
                    # Keep unchanged
                    modified_source[key] = entry.copy()
            
            # Create files
            source_file = temp_dir / "source.json"
            translation_file = temp_dir / "translation.json"
            
            with open(source_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": modified_source}, f, ensure_ascii=False, indent=2)
            
            with open(translation_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": translated_entries}, f, ensure_ascii=False, indent=2)
            
            # Mark changed entries
            marked = tracker.mark_changed_entries(str(source_file), str(translation_file))
            
            # Verify that modified entries are marked
            assert set(marked) == modified_keys, \
                f"Expected marked: {modified_keys}, got: {set(marked)}"
            
            # Verify the translation file has needs_review marks
            with open(translation_file, 'r', encoding='utf-8') as f:
                updated_data = json.load(f)
            
            for key in modified_keys:
                entry = updated_data["entries"][key]
                meta = entry.get("_meta", {})
                assert meta.get("needs_review") is True, \
                    f"Entry '{key}' should be marked as needs_review"
                assert "marked_at" in meta, \
                    f"Entry '{key}' should have marked_at timestamp"
                assert "new_source_hash" in meta, \
                    f"Entry '{key}' should have new_source_hash"
    
    @given(entries=entries_strategy)
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_unchanged_entries_not_marked(self, entries):
        """
        Property: Entries with unchanged source content should not be marked.
        
        Feature: translation-automation-workflow, Property: Unchanged not marked
        **Validates: Requirements 5.3, 8.3**
        """
        assume(len(entries) > 0)
        
        tracker = ProgressTracker()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            
            # Create source entries
            source_entries = {}
            for key in entries.keys():
                source_entries[key] = {
                    "name": f"Source_{key}",
                    "description": "Source description"
                }
            
            # Create translation entries with matching source_hash
            translated_entries = {}
            for key, source_entry in source_entries.items():
                source_hash = tracker._compute_content_hash(source_entry)
                translated_entries[key] = {
                    "name": f"翻译_{key}",
                    "description": "翻译描述",
                    "_meta": {
                        "source_hash": source_hash
                    }
                }
            
            source_file = temp_dir / "source.json"
            translation_file = temp_dir / "translation.json"
            
            with open(source_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": source_entries}, f, ensure_ascii=False, indent=2)
            
            with open(translation_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": translated_entries}, f, ensure_ascii=False, indent=2)
            
            # Mark changed entries (should be none)
            marked = tracker.mark_changed_entries(str(source_file), str(translation_file))
            
            assert len(marked) == 0, \
                f"No entries should be marked when source is unchanged, got: {marked}"
    
    @given(entries=entries_strategy)
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_already_marked_entries_not_remarked(self, entries):
        """
        Property: Entries already marked as needs_review should not be re-marked.
        
        Feature: translation-automation-workflow, Property: Idempotent marking
        **Validates: Requirements 5.3, 8.3**
        """
        assume(len(entries) > 0)
        
        tracker = ProgressTracker()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            
            # Create modified source entries
            source_entries = {}
            for key in entries.keys():
                source_entries[key] = {
                    "name": f"Modified_{key}",
                    "description": "Modified description"
                }
            
            # Create translation entries with old source_hash and already marked
            translated_entries = {}
            original_marked_at = "2024-01-01T00:00:00"
            for key in entries.keys():
                translated_entries[key] = {
                    "name": f"翻译_{key}",
                    "description": "翻译描述",
                    "_meta": {
                        "source_hash": "old_hash_that_doesnt_match",
                        "needs_review": True,
                        "marked_at": original_marked_at
                    }
                }
            
            source_file = temp_dir / "source.json"
            translation_file = temp_dir / "translation.json"
            
            with open(source_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": source_entries}, f, ensure_ascii=False, indent=2)
            
            with open(translation_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": translated_entries}, f, ensure_ascii=False, indent=2)
            
            # Mark changed entries
            marked = tracker.mark_changed_entries(str(source_file), str(translation_file))
            
            # Should not re-mark already marked entries
            assert len(marked) == 0, \
                f"Already marked entries should not be re-marked, got: {marked}"
            
            # Verify original marked_at is preserved
            with open(translation_file, 'r', encoding='utf-8') as f:
                updated_data = json.load(f)
            
            for key in entries.keys():
                entry = updated_data["entries"][key]
                assert entry["_meta"]["marked_at"] == original_marked_at, \
                    "Original marked_at should be preserved"
    
    @given(entries=entries_strategy)
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_clear_review_mark_updates_hash(self, entries):
        """
        Property: Clearing review mark should update source_hash and remove review flags.
        
        Feature: translation-automation-workflow, Property: Clear review
        **Validates: Requirements 5.3, 8.3**
        """
        assume(len(entries) > 0)
        
        tracker = ProgressTracker()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            
            # Create translation entries with needs_review mark
            new_source_hash = "new_hash_12345"
            translated_entries = {}
            for key in entries.keys():
                translated_entries[key] = {
                    "name": f"翻译_{key}",
                    "description": "翻译描述",
                    "_meta": {
                        "source_hash": "old_hash",
                        "needs_review": True,
                        "review_reason": "source_changed",
                        "marked_at": "2024-01-01T00:00:00",
                        "new_source_hash": new_source_hash
                    }
                }
            
            translation_file = temp_dir / "translation.json"
            with open(translation_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": translated_entries}, f, ensure_ascii=False, indent=2)
            
            # Clear review mark for first entry
            first_key = list(entries.keys())[0]
            result = tracker.clear_review_mark(str(translation_file), first_key)
            
            assert result is True, "Should successfully clear review mark"
            
            # Verify the entry is updated
            with open(translation_file, 'r', encoding='utf-8') as f:
                updated_data = json.load(f)
            
            entry = updated_data["entries"][first_key]
            meta = entry.get("_meta", {})
            
            assert meta.get("source_hash") == new_source_hash, \
                "source_hash should be updated to new_source_hash"
            assert "needs_review" not in meta, \
                "needs_review should be removed"
            assert "review_reason" not in meta, \
                "review_reason should be removed"
            assert "marked_at" not in meta, \
                "marked_at should be removed"
            assert "new_source_hash" not in meta, \
                "new_source_hash should be removed"
            assert "translated_at" in meta, \
                "translated_at should be added"
    
    @given(entries=entries_strategy)
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_get_entries_needing_review(self, entries):
        """
        Property: get_entries_needing_review should return all entries with needs_review=True.
        
        Feature: translation-automation-workflow, Property: Get review entries
        **Validates: Requirements 5.3, 8.3**
        """
        tracker = ProgressTracker()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            
            # Create entries with some marked for review
            translated_entries = {}
            expected_review = []
            for i, key in enumerate(entries.keys()):
                if i % 2 == 0:
                    # Mark for review
                    translated_entries[key] = {
                        "name": f"翻译_{key}",
                        "_meta": {
                            "needs_review": True
                        }
                    }
                    expected_review.append(key)
                else:
                    # Not marked
                    translated_entries[key] = {
                        "name": f"翻译_{key}",
                        "_meta": {}
                    }
            
            translation_file = temp_dir / "translation.json"
            with open(translation_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": translated_entries}, f, ensure_ascii=False, indent=2)
            
            # Get entries needing review
            needs_review = tracker.get_entries_needing_review(str(translation_file))
            
            assert set(needs_review) == set(expected_review), \
                f"Expected: {set(expected_review)}, got: {set(needs_review)}"
