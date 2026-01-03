"""测试数据模型"""

import pytest
from hypothesis import given, strategies as st

from automation.change_detector.models import ChangeReport
from automation.quality_checker.models import Issue, QualityReport
from automation.progress_tracker.models import CompendiumProgress, ProgressReport


class TestChangeReport:
    """ChangeReport 模型测试"""
    
    def test_empty_report_has_no_changes(self):
        """空报告应该没有变更"""
        report = ChangeReport(file_name="test.json")
        assert not report.has_changes
        assert report.total_entries == 0
    
    def test_report_with_added_entries_has_changes(self):
        """有新增条目的报告应该有变更"""
        report = ChangeReport(
            file_name="test.json",
            added_entries=["Entry1", "Entry2"]
        )
        assert report.has_changes
        assert report.total_entries == 2
    
    def test_report_with_modified_entries_has_changes(self):
        """有修改条目的报告应该有变更"""
        report = ChangeReport(
            file_name="test.json",
            modified_entries=["Entry1"]
        )
        assert report.has_changes
    
    def test_report_with_deleted_entries_has_changes(self):
        """有删除条目的报告应该有变更"""
        report = ChangeReport(
            file_name="test.json",
            deleted_entries=["Entry1"]
        )
        assert report.has_changes
    
    def test_total_entries_calculation(self):
        """测试总条目数计算"""
        report = ChangeReport(
            file_name="test.json",
            added_entries=["A1", "A2"],
            modified_entries=["M1"],
            deleted_entries=["D1", "D2", "D3"],
            unchanged_entries=["U1", "U2", "U3", "U4"]
        )
        assert report.total_entries == 10


class TestIssue:
    """Issue 模型测试"""
    
    def test_issue_str_representation(self):
        """测试 Issue 字符串表示"""
        issue = Issue(
            severity="error",
            type="placeholder",
            message="Missing placeholder {0}",
            location="Entry1.description"
        )
        assert "[ERROR]" in str(issue)
        assert "placeholder" in str(issue)
        assert "Entry1.description" in str(issue)


class TestQualityReport:
    """QualityReport 模型测试"""
    
    def test_empty_report_has_no_errors(self):
        """空报告应该没有错误"""
        report = QualityReport(file_name="test.json")
        assert not report.has_errors
        assert report.error_count == 0
        assert report.warning_count == 0
    
    def test_report_counts_by_severity(self):
        """测试按严重程度计数"""
        report = QualityReport(
            file_name="test.json",
            issues=[
                Issue(severity="error", type="html", message="msg1", location="loc1"),
                Issue(severity="error", type="html", message="msg2", location="loc2"),
                Issue(severity="warning", type="placeholder", message="msg3", location="loc3"),
                Issue(severity="info", type="glossary", message="msg4", location="loc4"),
            ]
        )
        assert report.error_count == 2
        assert report.warning_count == 1
        assert report.info_count == 1
        assert report.has_errors


class TestCompendiumProgress:
    """CompendiumProgress 模型测试"""
    
    def test_percentage_calculation(self):
        """测试百分比计算"""
        progress = CompendiumProgress(
            name="test-compendium",
            total=100,
            translated=75
        )
        assert progress.percentage == 75.0
    
    def test_percentage_with_zero_total(self):
        """总数为零时百分比应为 0"""
        progress = CompendiumProgress(name="empty", total=0, translated=0)
        assert progress.percentage == 0.0


class TestProgressReport:
    """ProgressReport 模型测试"""
    
    def test_completion_percentage(self):
        """测试完成百分比计算"""
        report = ProgressReport(
            total_entries=200,
            translated_entries=150
        )
        assert report.completion_percentage == 75.0
    
    def test_completion_percentage_with_zero_total(self):
        """总数为零时完成百分比应为 0"""
        report = ProgressReport(total_entries=0, translated_entries=0)
        assert report.completion_percentage == 0.0


# Property-based tests
class TestChangeReportProperties:
    """ChangeReport 属性测试"""
    
    @given(
        added=st.lists(st.text(min_size=1), max_size=10),
        modified=st.lists(st.text(min_size=1), max_size=10),
        deleted=st.lists(st.text(min_size=1), max_size=10),
        unchanged=st.lists(st.text(min_size=1), max_size=10)
    )
    @pytest.mark.property
    def test_total_entries_equals_sum_of_all_lists(
        self, added, modified, deleted, unchanged
    ):
        """
        Property: 总条目数应等于所有列表长度之和
        Feature: translation-automation-workflow, Property: Total entries consistency
        Validates: Data model integrity
        """
        report = ChangeReport(
            file_name="test.json",
            added_entries=added,
            modified_entries=modified,
            deleted_entries=deleted,
            unchanged_entries=unchanged
        )
        expected_total = len(added) + len(modified) + len(deleted) + len(unchanged)
        assert report.total_entries == expected_total


class TestProgressReportProperties:
    """ProgressReport 属性测试"""
    
    @given(
        total=st.integers(min_value=0, max_value=10000),
        translated=st.integers(min_value=0, max_value=10000)
    )
    @pytest.mark.property
    def test_percentage_is_bounded(self, total, translated):
        """
        Property: 完成百分比应在 0-100 之间（当 translated <= total 时）
        Feature: translation-automation-workflow, Property: Percentage bounds
        Validates: Requirements 5.1, 5.2
        """
        # 确保 translated 不超过 total
        translated = min(translated, total)
        
        report = ProgressReport(
            total_entries=total,
            translated_entries=translated
        )
        
        assert 0.0 <= report.completion_percentage <= 100.0
