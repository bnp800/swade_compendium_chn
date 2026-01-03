"""Change Detector 属性测试

Property 1: Change Detection Accuracy
Validates: Requirements 1.2, 8.1
"""

import pytest
from hypothesis import given, strategies as st, settings

from automation.change_detector import ChangeDetector, ChangeReport


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


class TestChangeDetectorProperties:
    """Change Detector 属性测试"""
    
    @given(
        old_entries=entries_strategy,
        new_entries=entries_strategy
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_change_detection_accuracy(self, old_entries, new_entries):
        """
        Property 1: Change Detection Accuracy
        
        *For any* pair of source JSON entries (old and new), the Change Detector 
        SHALL correctly identify all added, modified, and deleted entries, such that:
        - Every entry present in new but not in old is reported as "added"
        - Every entry present in both but with different content is reported as "modified"
        - Every entry present in old but not in new is reported as "deleted"
        - Every entry present in both with identical content is reported as "unchanged"
        
        Feature: translation-automation-workflow, Property 1: Change Detection Accuracy
        **Validates: Requirements 1.2, 8.1**
        """
        detector = ChangeDetector()
        report = detector.compare_entries(old_entries, new_entries)
        
        old_keys = set(old_entries.keys())
        new_keys = set(new_entries.keys())
        
        # Verify added entries: present in new but not in old
        expected_added = new_keys - old_keys
        assert set(report.added_entries) == expected_added, \
            f"Added entries mismatch: expected {expected_added}, got {set(report.added_entries)}"
        
        # Verify deleted entries: present in old but not in new
        expected_deleted = old_keys - new_keys
        assert set(report.deleted_entries) == expected_deleted, \
            f"Deleted entries mismatch: expected {expected_deleted}, got {set(report.deleted_entries)}"
        
        # Verify modified and unchanged entries
        common_keys = old_keys & new_keys
        reported_modified = set(report.modified_entries)
        reported_unchanged = set(report.unchanged_entries)
        
        # All common keys should be either modified or unchanged
        assert reported_modified | reported_unchanged == common_keys, \
            f"Common keys not fully categorized: common={common_keys}, modified={reported_modified}, unchanged={reported_unchanged}"
        
        # Modified and unchanged should be disjoint
        assert reported_modified & reported_unchanged == set(), \
            f"Entry cannot be both modified and unchanged"
        
        # Verify each modified entry actually has different content
        for key in reported_modified:
            assert old_entries[key] != new_entries[key], \
                f"Entry '{key}' reported as modified but content is identical"
        
        # Verify each unchanged entry actually has same content
        for key in reported_unchanged:
            assert old_entries[key] == new_entries[key], \
                f"Entry '{key}' reported as unchanged but content differs"
    
    @given(entries=entries_strategy)
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_comparing_identical_entries_yields_no_changes(self, entries):
        """
        Property: Comparing identical entries should yield no added, modified, or deleted entries.
        All entries should be reported as unchanged.
        
        Feature: translation-automation-workflow, Property: Identity comparison
        **Validates: Requirements 1.2, 8.1**
        """
        detector = ChangeDetector()
        report = detector.compare_entries(entries, entries)
        
        assert len(report.added_entries) == 0, "Identical entries should have no additions"
        assert len(report.modified_entries) == 0, "Identical entries should have no modifications"
        assert len(report.deleted_entries) == 0, "Identical entries should have no deletions"
        assert set(report.unchanged_entries) == set(entries.keys()), \
            "All entries should be unchanged when comparing identical data"
    
    @given(entries=entries_strategy)
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_comparing_empty_to_entries_yields_all_added(self, entries):
        """
        Property: Comparing empty old entries to new entries should report all as added.
        
        Feature: translation-automation-workflow, Property: Empty comparison
        **Validates: Requirements 1.2, 8.1**
        """
        detector = ChangeDetector()
        report = detector.compare_entries({}, entries)
        
        assert set(report.added_entries) == set(entries.keys()), \
            "All new entries should be reported as added"
        assert len(report.modified_entries) == 0
        assert len(report.deleted_entries) == 0
        assert len(report.unchanged_entries) == 0
    
    @given(entries=entries_strategy)
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_comparing_entries_to_empty_yields_all_deleted(self, entries):
        """
        Property: Comparing entries to empty new entries should report all as deleted.
        
        Feature: translation-automation-workflow, Property: Deletion comparison
        **Validates: Requirements 1.2, 8.1**
        """
        detector = ChangeDetector()
        report = detector.compare_entries(entries, {})
        
        assert set(report.deleted_entries) == set(entries.keys()), \
            "All old entries should be reported as deleted"
        assert len(report.added_entries) == 0
        assert len(report.modified_entries) == 0
        assert len(report.unchanged_entries) == 0
    
    @given(
        old_entries=entries_strategy,
        new_entries=entries_strategy
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_total_entries_covers_all_keys(self, old_entries, new_entries):
        """
        Property: The union of all reported entry lists should equal the union of old and new keys.
        
        Feature: translation-automation-workflow, Property: Complete coverage
        **Validates: Requirements 1.2, 8.1**
        """
        detector = ChangeDetector()
        report = detector.compare_entries(old_entries, new_entries)
        
        all_reported = (
            set(report.added_entries) |
            set(report.modified_entries) |
            set(report.deleted_entries) |
            set(report.unchanged_entries)
        )
        
        all_keys = set(old_entries.keys()) | set(new_entries.keys())
        
        assert all_reported == all_keys, \
            f"Reported entries should cover all keys: expected {all_keys}, got {all_reported}"



class TestPlaceholderFileCreation:
    """占位文件创建属性测试
    
    Property 14: Placeholder File Creation
    Validates: Requirements 1.4
    """
    
    @given(
        file_names=st.lists(
            st.text(min_size=1, max_size=30, alphabet=st.characters(
                whitelist_categories=('L', 'N'),
                whitelist_characters='-_.'
            )).filter(lambda x: x.endswith('.json') or not '.' in x),
            min_size=1,
            max_size=5,
            unique=True
        ),
        entries=entries_strategy
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_placeholder_file_creation(self, file_names, entries):
        """
        Property 14: Placeholder File Creation
        
        *For any* source file in en-US directory, if no corresponding file exists 
        in zh_Hans directory, the system SHALL create an empty placeholder file 
        with the correct structure.
        
        Feature: translation-automation-workflow, Property 14: Placeholder File Creation
        **Validates: Requirements 1.4**
        """
        import json
        import tempfile
        from pathlib import Path
        
        detector = ChangeDetector()
        
        # Ensure file names end with .json
        json_file_names = [
            f"{name}.json" if not name.endswith('.json') else name 
            for name in file_names
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            
            # Create source directory with files
            source_dir = temp_dir / "en-US"
            source_dir.mkdir(parents=True, exist_ok=True)
            
            target_dir = temp_dir / "zh_Hans"
            # Don't create target_dir yet - let sync_placeholder_files create it
            
            # Create source files
            for file_name in json_file_names:
                source_file = source_dir / file_name
                with open(source_file, 'w', encoding='utf-8') as f:
                    json.dump({"entries": entries}, f, ensure_ascii=False, indent=2)
            
            # Sync placeholder files
            created_files = detector.sync_placeholder_files(str(source_dir), str(target_dir))
            
            # Verify all source files have corresponding placeholder files
            for file_name in json_file_names:
                target_file = target_dir / file_name
                assert target_file.exists(), f"Placeholder file {file_name} should be created"
                
                # Verify placeholder file has correct structure
                with open(target_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                
                assert "entries" in content, "Placeholder file should have 'entries' key"
                assert isinstance(content["entries"], dict), "entries should be a dict"
    
    @given(entries=entries_strategy)
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_placeholder_not_created_if_exists(self, entries):
        """
        Property: If target file already exists, placeholder should not be created
        and existing content should be preserved.
        
        Feature: translation-automation-workflow, Property: Placeholder preservation
        **Validates: Requirements 1.4**
        """
        import json
        import tempfile
        from pathlib import Path
        
        detector = ChangeDetector()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            
            source_dir = temp_dir / "en-US"
            source_dir.mkdir(parents=True, exist_ok=True)
            target_dir = temp_dir / "zh_Hans"
            target_dir.mkdir(parents=True, exist_ok=True)
            
            file_name = "test.json"
            
            # Create source file
            source_file = source_dir / file_name
            with open(source_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": entries}, f, ensure_ascii=False, indent=2)
            
            # Create existing target file with different content
            existing_content = {"entries": {"ExistingEntry": {"name": "Existing"}}}
            target_file = target_dir / file_name
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(existing_content, f, ensure_ascii=False, indent=2)
            
            # Try to create placeholder
            result = detector.create_placeholder_file(str(source_file), str(target_dir))
            
            # Should return None (file not created)
            assert result is None, "Should not create placeholder when file exists"
            
            # Verify existing content is preserved
            with open(target_file, 'r', encoding='utf-8') as f:
                content = json.load(f)
            
            assert content == existing_content, "Existing content should be preserved"



class TestDeletedEntryHandling:
    """删除条目处理属性测试
    
    Property 15: Deleted Entry Handling
    Validates: Requirements 1.5
    """
    
    @given(
        source_entries=entries_strategy,
        translation_entries=entries_strategy
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_deleted_entry_marking(self, source_entries, translation_entries):
        """
        Property 15: Deleted Entry Handling
        
        *For any* entry that is deleted from the source file, the corresponding 
        translation entry SHALL be marked as "deprecated" rather than deleted, 
        preserving the translation for potential future use.
        
        Feature: translation-automation-workflow, Property 15: Deleted Entry Handling
        **Validates: Requirements 1.5**
        """
        import json
        import tempfile
        from pathlib import Path
        
        detector = ChangeDetector()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            
            source_file = temp_dir / "source.json"
            translation_file = temp_dir / "translation.json"
            
            # Create source file (simulating current state)
            with open(source_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": source_entries}, f, ensure_ascii=False, indent=2)
            
            # Create translation file (may have entries not in source)
            with open(translation_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": translation_entries}, f, ensure_ascii=False, indent=2)
            
            # Find entries that exist in translation but not in source (deleted entries)
            expected_deleted = set(translation_entries.keys()) - set(source_entries.keys())
            
            # Apply deleted entry marking
            report = detector.apply_deleted_entry_marking(
                str(source_file), 
                str(translation_file)
            )
            
            # Verify the report contains the correct deleted entries
            assert set(report.deleted_entries) == expected_deleted, \
                f"Expected deleted: {expected_deleted}, got: {set(report.deleted_entries)}"
            
            # Verify the translation file still contains all entries (not deleted)
            with open(translation_file, 'r', encoding='utf-8') as f:
                updated_data = json.load(f)
            
            updated_entries = updated_data.get("entries", {})
            
            # All original translation entries should still exist
            for key in translation_entries.keys():
                assert key in updated_entries, \
                    f"Entry '{key}' should not be deleted, only marked as deprecated"
            
            # Deleted entries should be marked as deprecated
            for key in expected_deleted:
                entry = updated_entries[key]
                assert detector.is_entry_deprecated(entry), \
                    f"Entry '{key}' should be marked as deprecated"
                assert "_meta" in entry, "Entry should have _meta field"
                assert entry["_meta"].get("deprecated") is True, \
                    "Entry should have deprecated=True in _meta"
    
    @given(entries=entries_strategy)
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_deprecated_entries_preserve_content(self, entries):
        """
        Property: Marking an entry as deprecated should preserve all original content.
        
        Feature: translation-automation-workflow, Property: Content preservation
        **Validates: Requirements 1.5**
        """
        import json
        import tempfile
        from pathlib import Path
        
        detector = ChangeDetector()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            
            # Create empty source file (all entries are "deleted")
            source_file = temp_dir / "source.json"
            with open(source_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": {}}, f, ensure_ascii=False, indent=2)
            
            # Create translation file with entries
            translation_file = temp_dir / "translation.json"
            with open(translation_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": entries}, f, ensure_ascii=False, indent=2)
            
            # Apply deleted entry marking
            detector.apply_deleted_entry_marking(str(source_file), str(translation_file))
            
            # Verify content is preserved
            with open(translation_file, 'r', encoding='utf-8') as f:
                updated_data = json.load(f)
            
            updated_entries = updated_data.get("entries", {})
            
            for key, original_entry in entries.items():
                assert key in updated_entries, f"Entry '{key}' should be preserved"
                updated_entry = updated_entries[key]
                
                # Original fields should be preserved
                for field in original_entry.keys():
                    if field != "_meta":
                        assert field in updated_entry, \
                            f"Field '{field}' should be preserved in entry '{key}'"
                        assert updated_entry[field] == original_entry[field], \
                            f"Field '{field}' content should be unchanged in entry '{key}'"
    
    @given(entries=entries_strategy)
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_already_deprecated_entries_not_remarked(self, entries):
        """
        Property: Entries already marked as deprecated should not be re-marked.
        
        Feature: translation-automation-workflow, Property: Idempotent marking
        **Validates: Requirements 1.5**
        """
        import json
        import tempfile
        from pathlib import Path
        
        detector = ChangeDetector()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            
            # Create empty source file
            source_file = temp_dir / "source.json"
            with open(source_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": {}}, f, ensure_ascii=False, indent=2)
            
            # Create translation file with already deprecated entries
            deprecated_entries = {}
            for key, entry in entries.items():
                deprecated_entries[key] = {
                    **entry,
                    "_meta": {
                        "deprecated": True,
                        "deprecated_at": "2024-01-01T00:00:00"
                    }
                }
            
            translation_file = temp_dir / "translation.json"
            with open(translation_file, 'w', encoding='utf-8') as f:
                json.dump({"entries": deprecated_entries}, f, ensure_ascii=False, indent=2)
            
            # Apply deleted entry marking
            report = detector.apply_deleted_entry_marking(str(source_file), str(translation_file))
            
            # No entries should be reported as newly deleted (they're already deprecated)
            assert len(report.deleted_entries) == 0, \
                "Already deprecated entries should not be reported as newly deleted"
            
            # Verify original deprecated_at timestamp is preserved
            with open(translation_file, 'r', encoding='utf-8') as f:
                updated_data = json.load(f)
            
            for key in entries.keys():
                entry = updated_data["entries"][key]
                assert entry["_meta"]["deprecated_at"] == "2024-01-01T00:00:00", \
                    "Original deprecated_at timestamp should be preserved"
