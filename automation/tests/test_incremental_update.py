"""Incremental Update 属性测试

Property 5: Incremental Update Preservation
Validates: Requirements 8.2
"""

import json
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, strategies as st, settings, assume

from automation.incremental_update import IncrementalUpdater


# Strategy for generating entry content (simulating Babele JSON entry structure)
entry_content_strategy = st.fixed_dictionaries({
    "name": st.text(min_size=1, max_size=50),
    "description": st.text(min_size=0, max_size=200),
    "category": st.text(min_size=0, max_size=30),
})

# Strategy for generating entries dict with valid keys
entries_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=30, alphabet=st.characters(
        whitelist_categories=('L', 'N'),
        whitelist_characters=' -_'
    )),
    values=entry_content_strategy,
    min_size=0,
    max_size=10
)


def create_translation_with_hash(source_entry: dict, translation_content: dict, updater: IncrementalUpdater) -> dict:
    """Create a translation entry with source hash metadata"""
    result = dict(translation_content)
    result["_meta"] = {
        "source_hash": updater._compute_content_hash(source_entry),
        "translated_at": "2024-01-01T00:00:00",
        "status": "translated"
    }
    return result


class TestIncrementalUpdatePreservation:
    """增量更新保留属性测试
    
    Property 5: Incremental Update Preservation
    Validates: Requirements 8.2
    """
    
    @given(
        source_entries=entries_strategy,
        translation_names=st.dictionaries(
            keys=st.text(min_size=1, max_size=30, alphabet=st.characters(
                whitelist_categories=('L', 'N'),
                whitelist_characters=' -_'
            )),
            values=st.text(min_size=1, max_size=50),  # Non-empty translation names
            min_size=0,
            max_size=10
        )
    )
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_incremental_update_preservation(self, source_entries, translation_names):
        """
        Property 5: Incremental Update Preservation
        
        *For any* source file update where some entries are unchanged, 
        the existing translations for unchanged entries SHALL be preserved 
        exactly as they were.
        
        Feature: translation-automation-workflow, Property 5: Incremental Update Preservation
        **Validates: Requirements 8.2**
        """
        # Skip if no source entries
        assume(len(source_entries) > 0)
        
        updater = IncrementalUpdater()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            
            source_file = temp_dir / "source.json"
            translation_file = temp_dir / "translation.json"
            
            # Create source file
            with open(source_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": source_entries}, f, ensure_ascii=False, indent=2)
            
            # Create translation file with translations for some entries
            # Each translation has the correct source_hash to indicate it's up-to-date
            translation_entries = {}
            for key in source_entries.keys():
                if key in translation_names:
                    # Create a translation with the correct source hash
                    translation_entries[key] = create_translation_with_hash(
                        source_entries[key],
                        {
                            "name": translation_names[key],
                            "description": f"翻译: {source_entries[key].get('description', '')}",
                            "category": "已翻译"
                        },
                        updater
                    )
            
            with open(translation_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": translation_entries}, f, ensure_ascii=False, indent=2)
            
            # Record original translations for unchanged entries
            original_translations = {k: dict(v) for k, v in translation_entries.items()}
            
            # Perform incremental update (source unchanged, so translations should be preserved)
            result = updater.incremental_update(
                str(source_file),
                str(translation_file),
                create_placeholders=True
            )
            
            # Load updated translation file
            with open(translation_file, 'r', encoding='utf-8') as f:
                updated_data = json.load(f)
            
            updated_entries = updated_data.get("entries", {})
            
            # Verify: all entries that had translations with correct source_hash
            # should be preserved exactly
            for key in result.preserved_entries:
                assert key in updated_entries, \
                    f"Preserved entry '{key}' should exist in updated file"
                
                original = original_translations.get(key, {})
                updated = updated_entries[key]
                
                # Check that translation content is preserved
                assert updated.get("name") == original.get("name"), \
                    f"Name should be preserved for entry '{key}'"
                assert updated.get("description") == original.get("description"), \
                    f"Description should be preserved for entry '{key}'"
                assert updated.get("category") == original.get("category"), \
                    f"Category should be preserved for entry '{key}'"
    
    @given(source_entries=entries_strategy)
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_unchanged_source_preserves_translation(self, source_entries):
        """
        Property: When source content is unchanged, existing translation 
        should be preserved exactly.
        
        Feature: translation-automation-workflow, Property: Source unchanged preservation
        **Validates: Requirements 8.2**
        """
        assume(len(source_entries) > 0)
        
        updater = IncrementalUpdater()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            
            source_file = temp_dir / "source.json"
            translation_file = temp_dir / "translation.json"
            
            # Create source file
            with open(source_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": source_entries}, f, ensure_ascii=False, indent=2)
            
            # Create translation file with all entries translated
            translation_entries = {}
            for key, source_entry in source_entries.items():
                translation_entries[key] = create_translation_with_hash(
                    source_entry,
                    {
                        "name": f"翻译_{key}",
                        "description": "已翻译的描述",
                        "category": "已翻译"
                    },
                    updater
                )
            
            with open(translation_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": translation_entries}, f, ensure_ascii=False, indent=2)
            
            # Record original translations
            original_translations = {k: dict(v) for k, v in translation_entries.items()}
            
            # Perform incremental update with same source (no changes)
            result = updater.incremental_update(
                str(source_file),
                str(translation_file),
                create_placeholders=True
            )
            
            # All entries should be preserved
            assert set(result.preserved_entries) == set(source_entries.keys()), \
                "All entries should be preserved when source is unchanged"
            
            # No entries should be added or modified
            assert len(result.added_entries) == 0, \
                "No entries should be added when source is unchanged"
            assert len(result.modified_entries) == 0, \
                "No entries should be modified when source is unchanged"
            
            # Verify content is preserved
            with open(translation_file, 'r', encoding='utf-8') as f:
                updated_data = json.load(f)
            
            for key in source_entries.keys():
                original = original_translations[key]
                updated = updated_data["entries"][key]
                
                assert updated["name"] == original["name"], \
                    f"Translation name should be preserved for '{key}'"

    @given(
        unchanged_entries=entries_strategy,
        new_entries=entries_strategy
    )
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_new_entries_do_not_affect_existing(self, unchanged_entries, new_entries):
        """
        Property: Adding new entries to source should not affect existing translations.
        
        Feature: translation-automation-workflow, Property: New entries isolation
        **Validates: Requirements 8.2, 8.4**
        """
        # Ensure no overlap between unchanged and new entries
        new_entries = {k: v for k, v in new_entries.items() if k not in unchanged_entries}
        assume(len(unchanged_entries) > 0)
        
        updater = IncrementalUpdater()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            
            source_file = temp_dir / "source.json"
            translation_file = temp_dir / "translation.json"
            
            # Combined source entries (unchanged + new)
            combined_source = {**unchanged_entries, **new_entries}
            
            # Create source file with combined entries
            with open(source_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": combined_source}, f, ensure_ascii=False, indent=2)
            
            # Create translation file with only unchanged entries translated
            translation_entries = {}
            for key, source_entry in unchanged_entries.items():
                translation_entries[key] = create_translation_with_hash(
                    source_entry,
                    {
                        "name": f"翻译_{key}",
                        "description": "已翻译的描述",
                        "category": "已翻译"
                    },
                    updater
                )
            
            with open(translation_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": translation_entries}, f, ensure_ascii=False, indent=2)
            
            # Record original translations
            original_translations = {k: dict(v) for k, v in translation_entries.items()}
            
            # Perform incremental update
            result = updater.incremental_update(
                str(source_file),
                str(translation_file),
                create_placeholders=True
            )
            
            # Verify unchanged entries are preserved
            assert set(result.preserved_entries) == set(unchanged_entries.keys()), \
                "Unchanged entries should be preserved"
            
            # Verify new entries are identified as added
            assert set(result.added_entries) == set(new_entries.keys()), \
                "New entries should be identified as added"
            
            # Verify original translations are unchanged
            with open(translation_file, 'r', encoding='utf-8') as f:
                updated_data = json.load(f)
            
            for key in unchanged_entries.keys():
                original = original_translations[key]
                updated = updated_data["entries"][key]
                
                assert updated["name"] == original["name"], \
                    f"Translation name should be preserved for '{key}'"
                assert updated["description"] == original["description"], \
                    f"Translation description should be preserved for '{key}'"


class TestIncrementalUpdateModifiedEntries:
    """测试修改条目的处理"""
    
    @given(
        source_entries=st.dictionaries(
            keys=st.text(min_size=1, max_size=30, alphabet=st.characters(
                whitelist_categories=('L', 'N'),
                whitelist_characters=' -_'
            )),
            values=entry_content_strategy,
            min_size=1,  # Ensure at least one entry
            max_size=10
        ),
        modification_suffix=st.text(min_size=1, max_size=50)
    )
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_modified_entries_marked_for_review(self, source_entries, modification_suffix):
        """
        Property: When source content changes, existing translation should be 
        preserved but marked for review.
        
        Feature: translation-automation-workflow, Property: Modified entry handling
        **Validates: Requirements 8.2, 8.3**
        """
        # Pick a random key to modify
        keys_to_modify = list(source_entries.keys())[:1]  # Modify first entry
        # Ensure modification is different by appending suffix
        modifications = {
            k: source_entries[k].get("description", "") + "_MODIFIED_" + modification_suffix 
            for k in keys_to_modify
        }
        
        updater = IncrementalUpdater()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            
            source_file = temp_dir / "source.json"
            translation_file = temp_dir / "translation.json"
            
            # Create initial source and translation
            initial_source = dict(source_entries)
            
            # Create translation file with all entries translated
            translation_entries = {}
            for key, source_entry in initial_source.items():
                translation_entries[key] = create_translation_with_hash(
                    source_entry,
                    {
                        "name": f"翻译_{key}",
                        "description": "已翻译的描述",
                        "category": "已翻译"
                    },
                    updater
                )
            
            with open(translation_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": translation_entries}, f, ensure_ascii=False, indent=2)
            
            # Modify source entries
            modified_source = dict(initial_source)
            for key, new_desc in modifications.items():
                if key in modified_source:
                    modified_source[key] = dict(modified_source[key])
                    modified_source[key]["description"] = new_desc
            
            # Create modified source file
            with open(source_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": modified_source}, f, ensure_ascii=False, indent=2)
            
            # Perform incremental update
            result = updater.incremental_update(
                str(source_file),
                str(translation_file),
                create_placeholders=True
            )
            
            # Verify modified entries are identified
            assert set(result.modified_entries) == set(modifications.keys()), \
                f"Modified entries should be identified: expected {set(modifications.keys())}, got {set(result.modified_entries)}"
            
            # Verify modified entries are marked for review
            with open(translation_file, 'r', encoding='utf-8') as f:
                updated_data = json.load(f)
            
            for key in modifications.keys():
                entry = updated_data["entries"][key]
                meta = entry.get("_meta", {})
                
                assert meta.get("needs_review") is True, \
                    f"Modified entry '{key}' should be marked for review"
                
                # Translation content should still be preserved
                assert entry["name"] == f"翻译_{key}", \
                    f"Translation name should be preserved for modified entry '{key}'"



class TestSmartMerge:
    """智能合并功能测试
    
    Validates: Requirements 8.5
    """
    
    def test_smart_merge_preserves_unchanged_fields(self):
        """测试智能合并保留未变更字段的翻译"""
        updater = IncrementalUpdater()
        
        old_source = {
            "name": "Test Edge",
            "description": "Original description",
            "category": "Combat"
        }
        
        new_source = {
            "name": "Test Edge",
            "description": "Original description",  # Unchanged
            "category": "Combat"  # Unchanged
        }
        
        existing_translation = {
            "name": "测试专长",
            "description": "原始描述",
            "category": "战斗"
        }
        
        merged, conflicts = updater.smart_merge(old_source, new_source, existing_translation)
        
        # All fields should be preserved
        assert merged["name"] == "测试专长"
        assert merged["description"] == "原始描述"
        assert merged["category"] == "战斗"
        assert len(conflicts) == 0
    
    def test_smart_merge_handles_added_fields(self):
        """测试智能合并处理新增字段"""
        updater = IncrementalUpdater()
        
        old_source = {
            "name": "Test Edge",
            "description": "Original description"
        }
        
        new_source = {
            "name": "Test Edge",
            "description": "Original description",
            "category": "Combat",  # New field
            "requirements": "Novice"  # New field
        }
        
        existing_translation = {
            "name": "测试专长",
            "description": "原始描述"
        }
        
        merged, conflicts = updater.smart_merge(old_source, new_source, existing_translation)
        
        # Original translations preserved
        assert merged["name"] == "测试专长"
        assert merged["description"] == "原始描述"
        
        # New fields added as empty placeholders
        assert merged["category"] == ""
        assert merged["requirements"] == ""
        
        # No conflicts for added fields
        assert len(conflicts) == 0
    
    def test_smart_merge_detects_modified_field_conflicts(self):
        """测试智能合并检测修改字段的冲突"""
        updater = IncrementalUpdater()
        
        old_source = {
            "name": "Test Edge",
            "description": "Original description"
        }
        
        new_source = {
            "name": "Test Edge",
            "description": "Modified description"  # Changed
        }
        
        existing_translation = {
            "name": "测试专长",
            "description": "原始描述"
        }
        
        merged, conflicts = updater.smart_merge(old_source, new_source, existing_translation)
        
        # Translation preserved
        assert merged["name"] == "测试专长"
        assert merged["description"] == "原始描述"
        
        # Conflict detected
        assert len(conflicts) == 1
        assert conflicts[0].field == "description"
        assert conflicts[0].conflict_type == "content_change"
        assert conflicts[0].source_value == "Modified description"
        assert conflicts[0].existing_translation == "原始描述"
    
    def test_smart_merge_detects_removed_field_conflicts(self):
        """测试智能合并检测删除字段的冲突"""
        updater = IncrementalUpdater()
        
        old_source = {
            "name": "Test Edge",
            "description": "Original description",
            "category": "Combat"
        }
        
        new_source = {
            "name": "Test Edge",
            "description": "Original description"
            # category removed
        }
        
        existing_translation = {
            "name": "测试专长",
            "description": "原始描述",
            "category": "战斗"
        }
        
        merged, conflicts = updater.smart_merge(old_source, new_source, existing_translation)
        
        # Translation preserved (including removed field)
        assert merged["name"] == "测试专长"
        assert merged["description"] == "原始描述"
        assert merged["category"] == "战斗"  # Still preserved
        
        # Conflict detected for removed field
        assert len(conflicts) == 1
        assert conflicts[0].field == "category"
        assert conflicts[0].conflict_type == "field_removed"
    
    def test_smart_merge_updates_metadata(self):
        """测试智能合并更新元数据"""
        updater = IncrementalUpdater()
        
        old_source = {"name": "Test"}
        new_source = {"name": "Test"}
        existing_translation = {"name": "测试"}
        
        merged, conflicts = updater.smart_merge(old_source, new_source, existing_translation)
        
        # Metadata should be updated
        assert "_meta" in merged
        assert "source_hash" in merged["_meta"]
        assert "merged_at" in merged["_meta"]
    
    def test_smart_merge_marks_conflicts_in_metadata(self):
        """测试智能合并在元数据中标记冲突"""
        updater = IncrementalUpdater()
        
        old_source = {"name": "Test", "description": "Old"}
        new_source = {"name": "Test", "description": "New"}
        existing_translation = {"name": "测试", "description": "旧"}
        
        merged, conflicts = updater.smart_merge(old_source, new_source, existing_translation)
        
        # Conflict metadata should be set
        assert merged["_meta"]["has_conflicts"] is True
        assert merged["_meta"]["conflict_count"] == 1
    
    def test_generate_conflict_report(self):
        """测试冲突报告生成"""
        from automation.incremental_update.updater import MergeConflict
        
        updater = IncrementalUpdater()
        
        conflicts = [
            MergeConflict(
                entry_key="Test Edge",
                field="description",
                source_value="New description",
                existing_translation="旧描述",
                conflict_type="content_change"
            ),
            MergeConflict(
                entry_key="Test Edge",
                field="category",
                source_value=None,
                existing_translation="战斗",
                conflict_type="field_removed"
            )
        ]
        
        report = updater.generate_conflict_report(conflicts)
        
        assert "# 合并冲突报告" in report
        assert "冲突数量: 2" in report
        assert "Test Edge" in report
        assert "description" in report
        assert "category" in report
        assert "content_change" in report
        assert "field_removed" in report
