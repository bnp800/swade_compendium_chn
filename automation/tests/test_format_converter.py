"""Format Converter 属性测试

Property 2: Format Conversion Round-Trip
*For any* valid Babele JSON file with HTML content, extracting text for translation
and then injecting translations back SHALL preserve:
- All HTML tags and their attributes
- All UUID links (@UUID[...]{})
- All Compendium links (@Compendium[...]{})
- All CSS class names
- All HTML entities
- All original links in their exact positions (links remain in English, pending post-processing)

Validates: Requirements 2.3, 3.1
"""

import pytest
import re
from hypothesis import given, strategies as st, settings, assume

from automation.format_converter import (
    FormatConverter,
    LinkPlaceholderManager,
    HTMLTextExtractor,
    ExtractedEntry,
)


# ============================================================================
# Strategies for generating test data
# ============================================================================

LOWERCASE = 'abcdefghijklmnopqrstuvwxyz'
DIGITS = '0123456789'
ALPHANUMERIC = LOWERCASE + DIGITS

simple_text = st.text(
    alphabet=st.sampled_from(LOWERCASE + DIGITS + ' '),
    min_size=1,
    max_size=50
).filter(lambda x: x.strip() and not x.isspace())

entry_name = st.text(
    alphabet=st.sampled_from(LOWERCASE + DIGITS + ' -_'),
    min_size=1,
    max_size=30
).filter(lambda x: x.strip() and not x.isspace())

uuid_ref = st.text(
    alphabet=st.sampled_from(ALPHANUMERIC + '.-'),
    min_size=5,
    max_size=20
).filter(lambda x: x and not x.startswith('.') and not x.endswith('.') and x[0].isalpha())

css_class = st.text(
    alphabet=st.sampled_from(LOWERCASE + '-'),
    min_size=2,
    max_size=15
).filter(lambda x: x and x[0].isalpha() and not x.endswith('-'))


@st.composite
def uuid_link(draw):
    """Generate a UUID link: @UUID[ref]{text}"""
    ref = draw(uuid_ref)
    text = draw(simple_text)
    return f"@UUID[{ref}]{{{text}}}"


@st.composite
def compendium_link(draw):
    """Generate a Compendium link: @Compendium[ref]{text}"""
    ref = draw(uuid_ref)
    text = draw(simple_text)
    return f"@Compendium[{ref}]{{{text}}}"


@st.composite
def html_paragraph(draw):
    """Generate an HTML paragraph with optional links"""
    text_parts = []
    text_parts.append(draw(simple_text))

    if draw(st.booleans()):
        link_type = draw(st.sampled_from(['uuid', 'compendium', 'none']))
        if link_type == 'uuid':
            text_parts.append(draw(uuid_link()))
        elif link_type == 'compendium':
            text_parts.append(draw(compendium_link()))

    if draw(st.booleans()):
        text_parts.append(draw(simple_text))

    content = ' '.join(text_parts)

    if draw(st.booleans()):
        css = draw(css_class)
        return f'<p class="{css}">{content}</p>'
    else:
        return f'<p>{content}</p>'


@st.composite
def html_article(draw):
    """Generate an HTML article with paragraphs"""
    num_paragraphs = draw(st.integers(min_value=1, max_value=3))
    paragraphs = [draw(html_paragraph()) for _ in range(num_paragraphs)]
    content = '\n'.join(paragraphs)

    if draw(st.booleans()):
        css = draw(css_class)
        return f'<article class="{css}">\n{content}\n</article>'
    else:
        return f'<article>\n{content}\n</article>'


@st.composite
def babele_entry(draw):
    """Generate a Babele entry with name and description"""
    name = draw(entry_name)
    description = draw(html_article())
    entry = {"name": name, "description": description}
    if draw(st.booleans()):
        entry["category"] = draw(entry_name)
    return name, entry


@st.composite
def babele_data(draw):
    """Generate Babele JSON data structure"""
    num_entries = draw(st.integers(min_value=1, max_value=3))
    entries = {}
    for i in range(num_entries):
        name, entry = draw(babele_entry())
        unique_name = f"{name}_{i}"
        entries[unique_name] = entry
    return {"entries": entries}


# ============================================================================
# Property 2: Format Conversion Round-Trip Tests
# ============================================================================

class TestFormatConversionRoundTrip:
    """
    Property 2: Format Conversion Round-Trip

    **Feature: translation-automation-workflow, Property 2: Format Conversion Round-Trip**
    **Validates: Requirements 2.3, 3.1**
    """

    @given(data=babele_data())
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_uuid_links_preserved_after_extraction(self, data):
        """UUID links are captured in placeholders during extraction.

        Validates: Requirements 2.3, 3.1
        """
        converter = FormatConverter()

        original_uuid_count = 0
        for entry in data['entries'].values():
            for field_value in entry.values():
                if isinstance(field_value, str):
                    original_uuid_count += len(re.findall(r'@UUID\[', field_value))

        entries = converter.extract_entries(data)

        extracted_uuid_count = 0
        for entry in entries:
            for ph_data in entry.placeholders.values():
                if ph_data.get('type') == 'uuid':
                    extracted_uuid_count += 1

        assert extracted_uuid_count == original_uuid_count, \
            f"Expected {original_uuid_count} UUID links, found {extracted_uuid_count}"

    @given(data=babele_data())
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_compendium_links_preserved_after_extraction(self, data):
        """Compendium links are captured in placeholders during extraction.

        Validates: Requirements 2.3, 3.1
        """
        converter = FormatConverter()

        original_comp_count = 0
        for entry in data['entries'].values():
            for field_value in entry.values():
                if isinstance(field_value, str):
                    original_comp_count += len(re.findall(r'@Compendium\[', field_value))

        entries = converter.extract_entries(data)

        extracted_comp_count = 0
        for entry in entries:
            for ph_data in entry.placeholders.values():
                if ph_data.get('type') == 'compendium':
                    extracted_comp_count += 1

        assert extracted_comp_count == original_comp_count, \
            f"Expected {original_comp_count} Compendium links, found {extracted_comp_count}"

    @given(data=babele_data())
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_html_structure_preserved_after_injection(self, data):
        """HTML tag structure is preserved after extract → inject round-trip.

        Validates: Requirements 2.3, 3.1
        """
        converter = FormatConverter()

        for key, entry in data['entries'].items():
            if 'description' not in entry:
                continue

            source_html = entry['description']
            original_tag_types = set(re.findall(r'</?([a-zA-Z]+)', source_html))

            extracted_text = converter.extract_text_from_html(source_html)
            result_html = converter.preserve_html_structure(source_html, extracted_text)

            result_tag_types = set(re.findall(r'</?([a-zA-Z]+)', result_html))

            for tag in ['p', 'article']:
                if tag in original_tag_types:
                    assert tag in result_tag_types, \
                        f"Tag <{tag}> was lost during round-trip"

    @given(data=babele_data())
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_css_classes_preserved_after_injection(self, data):
        """CSS classes are preserved after extract → inject round-trip.

        Validates: Requirements 2.3, 3.1
        """
        converter = FormatConverter()

        for key, entry in data['entries'].items():
            if 'description' not in entry:
                continue

            source_html = entry['description']
            original_classes = set(re.findall(r'class="([^"]*)"', source_html))
            if not original_classes:
                continue

            extracted_text = converter.extract_text_from_html(source_html)
            result_html = converter.preserve_html_structure(source_html, extracted_text)
            result_classes = set(re.findall(r'class="([^"]*)"', result_html))

            for css_cls in original_classes:
                assert css_cls in result_classes, \
                    f"CSS class '{css_cls}' was lost during round-trip"

    @given(data=babele_data())
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_links_preserved_at_original_positions_after_injection(self, data):
        """Links remain in their original paragraph after injection.

        For any Babele JSON with links in specific paragraphs, after extracting
        and injecting translations, each link should still be in the same
        paragraph (by index) as in the source.

        Validates: Requirements 2.3, 3.1
        """
        converter = FormatConverter()

        for key, entry in data['entries'].items():
            if 'description' not in entry:
                continue

            source_html = entry['description']
            source_paragraphs = re.findall(r'<p[^>]*>.*?</p>', source_html, re.DOTALL)
            if not source_paragraphs:
                continue

            # Map: paragraph index → set of link refs in that paragraph
            source_link_map = {}
            for i, para in enumerate(source_paragraphs):
                refs = set(re.findall(r'@(?:UUID|Compendium)\[([^\]]+)\]', para))
                if refs:
                    source_link_map[i] = refs

            if not source_link_map:
                continue

            extracted_text = converter.extract_text_from_html(source_html)
            result_html = converter.preserve_html_structure(source_html, extracted_text)
            result_paragraphs = re.findall(r'<p[^>]*>.*?</p>', result_html, re.DOTALL)

            for para_idx, expected_refs in source_link_map.items():
                if para_idx < len(result_paragraphs):
                    result_refs = set(re.findall(
                        r'@(?:UUID|Compendium)\[([^\]]+)\]',
                        result_paragraphs[para_idx]
                    ))
                    assert expected_refs == result_refs, \
                        f"Links in paragraph {para_idx} changed: {expected_refs} -> {result_refs}"

    @given(data=babele_data())
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_extracted_text_contains_no_link_syntax(self, data):
        """Extracted source_text should contain no @UUID or @Compendium syntax.

        Validates: Requirements 2.1, 2.2
        """
        converter = FormatConverter()
        entries = converter.extract_entries(data)

        for entry in entries:
            assert '@UUID[' not in entry.source_text, \
                f"source_text for {entry.key}.{entry.field} contains @UUID link syntax"
            assert '@Compendium[' not in entry.source_text, \
                f"source_text for {entry.key}.{entry.field} contains @Compendium link syntax"

    @given(data=babele_data())
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_extracted_text_contains_no_html_tags(self, data):
        """Extracted source_text should contain no HTML tags.

        Validates: Requirements 2.2
        """
        converter = FormatConverter()
        entries = converter.extract_entries(data)

        for entry in entries:
            # Check no HTML tags remain (allow < and > in non-tag contexts)
            html_tags = re.findall(r'</?[a-zA-Z][^>]*>', entry.source_text)
            assert not html_tags, \
                f"source_text for {entry.key}.{entry.field} contains HTML tags: {html_tags}"


# ============================================================================
# LinkPlaceholderManager Tests
# ============================================================================

class TestLinkPlaceholderManager:
    """Tests for LinkPlaceholderManager"""

    @given(ref=uuid_ref, text=simple_text)
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_uuid_link_round_trip(self, ref, text):
        """UUID links can be extracted and restored exactly"""
        manager = LinkPlaceholderManager()
        original = f"@UUID[{ref}]{{{text}}}"
        processed, placeholders = manager.extract_links(original)
        assert len(placeholders) == 1
        restored = manager.restore_links(processed, placeholders)
        assert restored == original

    @given(ref=uuid_ref, text=simple_text)
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_compendium_link_round_trip(self, ref, text):
        """Compendium links can be extracted and restored exactly"""
        manager = LinkPlaceholderManager()
        original = f"@Compendium[{ref}]{{{text}}}"
        processed, placeholders = manager.extract_links(original)
        assert len(placeholders) == 1
        restored = manager.restore_links(processed, placeholders)
        assert restored == original

    @given(ref=uuid_ref)
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_plain_uuid_link_round_trip(self, ref):
        """Plain UUID links (no display text) can be extracted and restored"""
        manager = LinkPlaceholderManager()
        original = f"@UUID[{ref}]"
        processed, placeholders = manager.extract_links(original)
        assert len(placeholders) == 1
        restored = manager.restore_links(processed, placeholders)
        assert restored == original

    @given(ref=uuid_ref)
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_plain_compendium_link_round_trip(self, ref):
        """Plain Compendium links (no display text) can be extracted and restored"""
        manager = LinkPlaceholderManager()
        original = f"@Compendium[{ref}]"
        processed, placeholders = manager.extract_links(original)
        assert len(placeholders) == 1
        restored = manager.restore_links(processed, placeholders)
        assert restored == original

    @given(ref=uuid_ref, text=simple_text)
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_strip_links_removes_all_link_syntax(self, ref, text):
        """strip_links completely removes link syntax from content"""
        manager = LinkPlaceholderManager()
        content = f"before @UUID[{ref}]{{{text}}} middle @Compendium[{ref}]{{{text}}} after"
        stripped, links = manager.strip_links(content)
        assert '@UUID[' not in stripped
        assert '@Compendium[' not in stripped
        assert len(links) == 2


# ============================================================================
# HTMLTextExtractor Tests
# ============================================================================

class TestHTMLTextExtractor:
    """Tests for HTMLTextExtractor"""

    @given(text=simple_text)
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_text_extraction_preserves_content(self, text):
        """Text content is preserved after extraction from simple HTML"""
        extractor = HTMLTextExtractor()
        html = f"<p>{text}</p>"
        extractor.feed(html)
        extracted = extractor.get_text()
        normalized_text = ' '.join(text.split())
        assert normalized_text in extracted or extracted in normalized_text


# ============================================================================
# Property 3: Link Preservation Tests (extract → inject round-trip)
# ============================================================================

class TestUUIDLinkPreservation:
    """
    Property 3: UUID Link Preservation

    *For any* HTML content containing UUID or Compendium links, after translation
    injection, the number and content of all links SHALL remain identical to the source.

    **Feature: translation-automation-workflow, Property 3: UUID Link Preservation**
    **Validates: Requirements 2.4, 7.3**
    """

    @given(ref=uuid_ref, text=simple_text, surrounding_text=simple_text)
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_uuid_link_count_preserved(self, ref, text, surrounding_text):
        """UUID link count is preserved after extract → inject.

        Validates: Requirements 2.4, 7.3
        """
        converter = FormatConverter()
        source_html = f'<p>{surrounding_text} @UUID[{ref}]{{{text}}} more text</p>'
        original_count = len(re.findall(r'@UUID\[', source_html))

        extracted_text = converter.extract_text_from_html(source_html)
        result_html = converter.preserve_html_structure(source_html, extracted_text)
        result_count = len(re.findall(r'@UUID\[', result_html))

        assert result_count == original_count, \
            f"UUID link count changed: {original_count} -> {result_count}"

    @given(ref=uuid_ref, text=simple_text, surrounding_text=simple_text)
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_uuid_link_ref_preserved(self, ref, text, surrounding_text):
        """UUID link references are preserved after extract → inject.

        Validates: Requirements 2.4, 7.3
        """
        converter = FormatConverter()
        source_html = f'<p>{surrounding_text} @UUID[{ref}]{{{text}}} more text</p>'
        original_refs = re.findall(r'@UUID\[([^\]]+)\]', source_html)

        extracted_text = converter.extract_text_from_html(source_html)
        result_html = converter.preserve_html_structure(source_html, extracted_text)
        result_refs = re.findall(r'@UUID\[([^\]]+)\]', result_html)

        assert set(original_refs) == set(result_refs), \
            f"UUID refs changed: {original_refs} -> {result_refs}"

    @given(ref=uuid_ref, text=simple_text, surrounding_text=simple_text)
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_compendium_link_count_preserved(self, ref, text, surrounding_text):
        """Compendium link count is preserved after extract → inject.

        Validates: Requirements 2.4, 7.3
        """
        converter = FormatConverter()
        source_html = f'<p>{surrounding_text} @Compendium[{ref}]{{{text}}} more text</p>'
        original_count = len(re.findall(r'@Compendium\[', source_html))

        extracted_text = converter.extract_text_from_html(source_html)
        result_html = converter.preserve_html_structure(source_html, extracted_text)
        result_count = len(re.findall(r'@Compendium\[', result_html))

        assert result_count == original_count, \
            f"Compendium link count changed: {original_count} -> {result_count}"

    @given(ref=uuid_ref, text=simple_text, surrounding_text=simple_text)
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_compendium_link_ref_preserved(self, ref, text, surrounding_text):
        """Compendium link references are preserved after extract → inject.

        Validates: Requirements 2.4, 7.3
        """
        converter = FormatConverter()
        source_html = f'<p>{surrounding_text} @Compendium[{ref}]{{{text}}} more text</p>'
        original_refs = re.findall(r'@Compendium\[([^\]]+)\]', source_html)

        extracted_text = converter.extract_text_from_html(source_html)
        result_html = converter.preserve_html_structure(source_html, extracted_text)
        result_refs = re.findall(r'@Compendium\[([^\]]+)\]', result_html)

        assert set(original_refs) == set(result_refs), \
            f"Compendium refs changed: {original_refs} -> {result_refs}"

    @given(data=babele_data())
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_all_links_preserved_in_babele_data(self, data):
        """All links are preserved in Babele data after extract → inject.

        Validates: Requirements 2.4, 7.3
        """
        converter = FormatConverter()

        for key, entry in data['entries'].items():
            if 'description' not in entry:
                continue

            source_html = entry['description']
            original_uuid_count = len(re.findall(r'@UUID\[', source_html))
            original_comp_count = len(re.findall(r'@Compendium\[', source_html))

            extracted_text = converter.extract_text_from_html(source_html)
            result_html = converter.preserve_html_structure(source_html, extracted_text)

            result_uuid_count = len(re.findall(r'@UUID\[', result_html))
            result_comp_count = len(re.findall(r'@Compendium\[', result_html))

            assert result_uuid_count == original_uuid_count, \
                f"UUID count changed for {key}: {original_uuid_count} -> {result_uuid_count}"
            assert result_comp_count == original_comp_count, \
                f"Compendium count changed for {key}: {original_comp_count} -> {result_comp_count}"

    @given(ref=uuid_ref, text=simple_text, surrounding_text=simple_text)
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_uuid_display_text_preserved(self, ref, text, surrounding_text):
        """UUID link display text is preserved exactly after injection.

        Validates: Requirements 2.4, 3.1
        """
        converter = FormatConverter()
        source_html = f'<p>{surrounding_text} @UUID[{ref}]{{{text}}} more text</p>'

        extracted_text = converter.extract_text_from_html(source_html)
        result_html = converter.preserve_html_structure(source_html, extracted_text)

        # The full link including display text should be preserved
        original_links = re.findall(r'@UUID\[[^\]]+\]\{[^}]+\}', source_html)
        result_links = re.findall(r'@UUID\[[^\]]+\]\{[^}]+\}', result_html)

        assert set(original_links) == set(result_links), \
            f"UUID links with display text changed: {original_links} -> {result_links}"
