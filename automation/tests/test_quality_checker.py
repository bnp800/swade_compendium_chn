"""Quality Checker 属性测试

Property 9: HTML Tag Balance
Property 10: Placeholder Detection
Validates: Requirements 7.1, 7.2
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

from automation.quality_checker import QualityChecker, Issue, QualityReport


# ============================================================================
# Strategies for generating test data
# ============================================================================

# Strategy for generating placeholder patterns
placeholder_strategy = st.sampled_from([
    "{0}", "{1}", "{2}", "{3}",
    "{name}", "{value}", "{count}", "{item}",
    "{{variable}}", "{{name}}", "{{count}}",
    "%s", "%d", "%i", "%f", "%x",
    "%(name)s", "%(count)d", "%(value)f"
])

# Strategy for generating simple text without placeholders
simple_text_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=('L', 'N', 'P', 'S', 'Zs'),
        blacklist_characters='{}'
    ),
    min_size=0,
    max_size=100
)

# Strategy for generating HTML tag names
html_tag_strategy = st.sampled_from([
    'p', 'div', 'span', 'article', 'section', 'strong', 'em', 'b', 'i', 'u',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'a', 'table', 'tr', 'td'
])

# Strategy for self-closing tags
self_closing_tag_strategy = st.sampled_from([
    'br', 'hr', 'img', 'input'
])


# ============================================================================
# Property 10: Placeholder Detection Tests
# ============================================================================

class TestPlaceholderDetection:
    """占位符检测属性测试
    
    Property 10: Placeholder Detection
    Validates: Requirements 7.1
    """
    
    @given(
        placeholders=st.lists(placeholder_strategy, min_size=1, max_size=5, unique=True),
        text_parts=st.lists(simple_text_strategy, min_size=2, max_size=6)
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_placeholder_detection_finds_all_placeholders(self, placeholders, text_parts):
        """
        Property 10: Placeholder Detection
        
        *For any* translation where the source contains placeholders (e.g., {0}, {{variable}}),
        the Quality Checker SHALL verify that all placeholders are present in the translation.
        
        This test verifies that when source has placeholders and translation is missing some,
        the checker correctly identifies the missing placeholders.
        
        Feature: translation-automation-workflow, Property 10: Placeholder Detection
        **Validates: Requirements 7.1**
        """
        checker = QualityChecker()
        
        # Build source text with all placeholders
        source_parts = list(text_parts[:len(placeholders) + 1])
        while len(source_parts) < len(placeholders) + 1:
            source_parts.append("")
        
        source = ""
        for i, placeholder in enumerate(placeholders):
            source += source_parts[i] + placeholder
        source += source_parts[-1]
        
        # Build translation with only some placeholders (missing the last one)
        translation_placeholders = placeholders[:-1] if len(placeholders) > 1 else []
        translation = ""
        for i, placeholder in enumerate(translation_placeholders):
            translation += source_parts[i] + placeholder
        translation += source_parts[-1]
        
        issues = checker.check_placeholders(source, translation, "test.entry")
        
        # Should find the missing placeholder(s)
        missing_placeholders = set(placeholders) - set(translation_placeholders)
        error_messages = [i.message for i in issues if i.severity == "error"]
        
        for missing in missing_placeholders:
            found = any(missing in msg for msg in error_messages)
            assert found, f"Missing placeholder '{missing}' should be reported"
    
    @given(
        placeholders=st.lists(placeholder_strategy, min_size=1, max_size=5, unique=True),
        text_parts=st.lists(simple_text_strategy, min_size=2, max_size=6)
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_placeholder_detection_no_issues_when_all_present(self, placeholders, text_parts):
        """
        Property: When all placeholders are present in translation, no errors should be reported.
        
        Feature: translation-automation-workflow, Property 10: Placeholder Detection
        **Validates: Requirements 7.1**
        """
        checker = QualityChecker()
        
        # Build source text with placeholders
        source_parts = list(text_parts[:len(placeholders) + 1])
        while len(source_parts) < len(placeholders) + 1:
            source_parts.append("")
        
        source = ""
        for i, placeholder in enumerate(placeholders):
            source += source_parts[i] + placeholder
        source += source_parts[-1]
        
        # Translation has all the same placeholders (just different text around them)
        translation = ""
        for i, placeholder in enumerate(placeholders):
            translation += "翻译文本" + placeholder
        translation += "结束"
        
        issues = checker.check_placeholders(source, translation, "test.entry")
        
        # Should have no errors (all placeholders present)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0, f"No errors expected when all placeholders present, got: {errors}"
    
    @given(
        extra_placeholders=st.lists(placeholder_strategy, min_size=1, max_size=3, unique=True)
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_placeholder_detection_warns_on_extra_placeholders(self, extra_placeholders):
        """
        Property: When translation has extra placeholders not in source, warnings should be reported.
        
        Feature: translation-automation-workflow, Property 10: Placeholder Detection
        **Validates: Requirements 7.1**
        """
        checker = QualityChecker()
        
        source = "Simple text without placeholders"
        translation = "翻译文本 " + " ".join(extra_placeholders)
        
        issues = checker.check_placeholders(source, translation, "test.entry")
        
        # Should have warnings for extra placeholders
        warnings = [i for i in issues if i.severity == "warning"]
        assert len(warnings) == len(extra_placeholders), \
            f"Expected {len(extra_placeholders)} warnings for extra placeholders"


# ============================================================================
# Property 9: HTML Tag Balance Tests
# ============================================================================

class TestHTMLTagBalance:
    """HTML 标签平衡属性测试
    
    Property 9: HTML Tag Balance
    Validates: Requirements 7.2
    """
    
    @given(
        tag_names=st.lists(html_tag_strategy, min_size=1, max_size=5),
        text_content=st.text(min_size=0, max_size=50, alphabet=st.characters(
            whitelist_categories=('L', 'N', 'Zs'),
            blacklist_characters='<>'
        ))
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_balanced_html_has_no_errors(self, tag_names, text_content):
        """
        Property 9: HTML Tag Balance
        
        *For any* translated HTML content with properly balanced tags,
        the Quality Checker SHALL report no tag balance errors.
        
        Feature: translation-automation-workflow, Property 9: HTML Tag Balance
        **Validates: Requirements 7.2**
        """
        checker = QualityChecker()
        
        # Build balanced HTML by nesting tags
        html = text_content
        for tag in tag_names:
            html = f"<{tag}>{html}</{tag}>"
        
        # Source and translation have same structure
        source = html
        translation = html.replace(text_content, "翻译内容") if text_content else html
        
        issues = checker.check_html_tags(source, translation, "test.entry")
        
        # Should have no errors for balanced HTML
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0, f"Balanced HTML should have no errors, got: {errors}"
    
    @given(
        tag_name=html_tag_strategy,
        text_content=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('L', 'N', 'Zs'),
            blacklist_characters='<>'
        ))
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_unclosed_tag_detected(self, tag_name, text_content):
        """
        Property: Unclosed tags should be detected and reported as errors.
        
        Feature: translation-automation-workflow, Property 9: HTML Tag Balance
        **Validates: Requirements 7.2**
        """
        checker = QualityChecker()
        
        # Source has balanced tags
        source = f"<{tag_name}>{text_content}</{tag_name}>"
        # Translation is missing closing tag
        translation = f"<{tag_name}>{text_content}"
        
        issues = checker.check_html_tags(source, translation, "test.entry")
        
        # Should detect the unclosed tag
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) > 0, f"Unclosed tag '<{tag_name}>' should be detected"
        
        # Error message should mention the unclosed tag
        error_messages = " ".join(i.message for i in errors)
        assert tag_name in error_messages, f"Error should mention tag '{tag_name}'"
    
    @given(
        tag_name=html_tag_strategy,
        text_content=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('L', 'N', 'Zs'),
            blacklist_characters='<>'
        ))
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_extra_closing_tag_detected(self, tag_name, text_content):
        """
        Property: Extra closing tags should be detected and reported as errors.
        
        Feature: translation-automation-workflow, Property 9: HTML Tag Balance
        **Validates: Requirements 7.2**
        """
        checker = QualityChecker()
        
        # Source has balanced tags
        source = f"<{tag_name}>{text_content}</{tag_name}>"
        # Translation has extra closing tag
        translation = f"<{tag_name}>{text_content}</{tag_name}></{tag_name}>"
        
        issues = checker.check_html_tags(source, translation, "test.entry")
        
        # Should detect the extra closing tag
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) > 0, f"Extra closing tag '</{tag_name}>' should be detected"
    
    @given(
        self_closing_tag=self_closing_tag_strategy,
        text_content=st.text(min_size=0, max_size=50, alphabet=st.characters(
            whitelist_categories=('L', 'N', 'Zs'),
            blacklist_characters='<>'
        ))
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_self_closing_tags_handled_correctly(self, self_closing_tag, text_content):
        """
        Property: Self-closing tags (br, hr, img, etc.) should not require closing tags.
        
        Feature: translation-automation-workflow, Property 9: HTML Tag Balance
        **Validates: Requirements 7.2**
        """
        checker = QualityChecker()
        
        # HTML with self-closing tag
        html = f"<p>{text_content}<{self_closing_tag}>{text_content}</p>"
        
        issues = checker.check_html_tags(html, html, "test.entry")
        
        # Should have no errors for self-closing tags
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0, f"Self-closing tag '<{self_closing_tag}>' should not cause errors"
