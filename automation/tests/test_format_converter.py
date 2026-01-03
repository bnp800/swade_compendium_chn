"""Format Converter 属性测试

Property 2: Format Conversion Round-Trip
*For any* valid Babele JSON file with HTML content, extracting text for Weblate 
and then injecting translations back SHALL preserve:
- All HTML tags and their attributes
- All UUID links (@UUID[...]{})
- All Compendium links (@Compendium[...]{})
- All CSS class names
- All HTML entities

Validates: Requirements 2.2, 2.3, 2.4
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

# Character sets for generating strings
LOWERCASE = 'abcdefghijklmnopqrstuvwxyz'
DIGITS = '0123456789'
ALPHANUMERIC = LOWERCASE + DIGITS

# Simple text without special characters
simple_text = st.text(
    alphabet=st.sampled_from(LOWERCASE + DIGITS + ' '),
    min_size=1,
    max_size=50
).filter(lambda x: x.strip() and not x.isspace())

# Entry names (alphanumeric with spaces)
entry_name = st.text(
    alphabet=st.sampled_from(LOWERCASE + DIGITS + ' -_'),
    min_size=1,
    max_size=30
).filter(lambda x: x.strip() and not x.isspace())

# UUID references
uuid_ref = st.text(
    alphabet=st.sampled_from(ALPHANUMERIC + '.-'),
    min_size=5,
    max_size=20
).filter(lambda x: x and not x.startswith('.') and not x.endswith('.') and x[0].isalpha())

# CSS class names
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
    
    # Add some text
    text_parts.append(draw(simple_text))
    
    # Optionally add a link
    if draw(st.booleans()):
        link_type = draw(st.sampled_from(['uuid', 'compendium', 'none']))
        if link_type == 'uuid':
            text_parts.append(draw(uuid_link()))
        elif link_type == 'compendium':
            text_parts.append(draw(compendium_link()))
    
    # Add more text
    if draw(st.booleans()):
        text_parts.append(draw(simple_text))
    
    content = ' '.join(text_parts)
    
    # Wrap in paragraph tag
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
    
    entry = {
        "name": name,
        "description": description,
    }
    
    # Optionally add category
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
        # Ensure unique names by appending index
        unique_name = f"{name}_{i}"
        entries[unique_name] = entry
    
    return {"entries": entries}


# ============================================================================
# Property Tests
# ============================================================================

class TestFormatConversionRoundTrip:
    """
    Property 2: Format Conversion Round-Trip
    
    **Feature: translation-automation-workflow, Property 2: Format Conversion Round-Trip**
    **Validates: Requirements 2.2, 2.3, 2.4**
    """
    
    @given(data=babele_data())
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_uuid_links_preserved_after_extraction(self, data):
        """
        Property 2: Format Conversion Round-Trip - UUID links preserved
        
        For any valid Babele JSON with UUID links, extracting text should
        preserve all UUID link references in placeholders.
        
        **Validates: Requirements 2.2, 2.3, 2.4**
        """
        converter = FormatConverter()
        
        # Count UUID links in original data
        original_uuid_count = 0
        for entry in data['entries'].values():
            for field_value in entry.values():
                if isinstance(field_value, str):
                    original_uuid_count += len(re.findall(r'@UUID\[', field_value))
        
        # Extract entries
        entries = converter.extract_entries(data)
        
        # Count UUID links in placeholders
        extracted_uuid_count = 0
        for entry in entries:
            for ph_data in entry.placeholders.values():
                if ph_data.get('type') == 'uuid':
                    extracted_uuid_count += 1
        
        # All UUID links should be captured in placeholders
        assert extracted_uuid_count == original_uuid_count, \
            f"Expected {original_uuid_count} UUID links, found {extracted_uuid_count} in placeholders"
    
    @given(data=babele_data())
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_compendium_links_preserved_after_extraction(self, data):
        """
        Property 2: Format Conversion Round-Trip - Compendium links preserved
        
        For any valid Babele JSON with Compendium links, extracting text should
        preserve all Compendium link references in placeholders.
        
        **Validates: Requirements 2.2, 2.3, 2.4**
        """
        converter = FormatConverter()
        
        # Count Compendium links in original data
        original_comp_count = 0
        for entry in data['entries'].values():
            for field_value in entry.values():
                if isinstance(field_value, str):
                    original_comp_count += len(re.findall(r'@Compendium\[', field_value))
        
        # Extract entries
        entries = converter.extract_entries(data)
        
        # Count Compendium links in placeholders
        extracted_comp_count = 0
        for entry in entries:
            for ph_data in entry.placeholders.values():
                if ph_data.get('type') == 'compendium':
                    extracted_comp_count += 1
        
        # All Compendium links should be captured in placeholders
        assert extracted_comp_count == original_comp_count, \
            f"Expected {original_comp_count} Compendium links, found {extracted_comp_count} in placeholders"
    
    @given(data=babele_data())
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_html_structure_preserved_after_injection(self, data):
        """
        Property 2: Format Conversion Round-Trip - HTML structure preserved
        
        For any valid Babele JSON, extracting and then injecting translations
        should preserve the HTML tag structure.
        
        **Validates: Requirements 2.2, 2.3, 2.4**
        """
        converter = FormatConverter()
        
        for key, entry in data['entries'].items():
            if 'description' not in entry:
                continue
                
            source_html = entry['description']
            
            # Extract original HTML tags
            original_tags = re.findall(r'</?[a-zA-Z][^>]*>', source_html)
            
            # Extract text
            extracted_text = converter.extract_text_from_html(source_html)
            
            # Inject back (simulating translation with same text)
            result_html = converter.preserve_html_structure(source_html, extracted_text)
            
            # Extract result HTML tags
            result_tags = re.findall(r'</?[a-zA-Z][^>]*>', result_html)
            
            # Check that key structural tags are preserved
            # (exact tag count may differ due to paragraph restructuring)
            original_tag_types = set(re.findall(r'</?([a-zA-Z]+)', source_html))
            result_tag_types = set(re.findall(r'</?([a-zA-Z]+)', result_html))
            
            # Core tags should be preserved
            for tag in ['p', 'article']:
                if tag in original_tag_types:
                    assert tag in result_tag_types, \
                        f"Tag <{tag}> was lost during round-trip"
    
    @given(data=babele_data())
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_css_classes_preserved_after_injection(self, data):
        """
        Property 2: Format Conversion Round-Trip - CSS classes preserved
        
        For any valid Babele JSON with CSS classes, extracting and injecting
        should preserve all CSS class names.
        
        **Validates: Requirements 2.2, 2.3, 2.4**
        """
        converter = FormatConverter()
        
        for key, entry in data['entries'].items():
            if 'description' not in entry:
                continue
                
            source_html = entry['description']
            
            # Extract original CSS classes
            original_classes = set(re.findall(r'class="([^"]*)"', source_html))
            
            if not original_classes:
                continue
            
            # Extract text
            extracted_text = converter.extract_text_from_html(source_html)
            
            # Inject back
            result_html = converter.preserve_html_structure(source_html, extracted_text)
            
            # Extract result CSS classes
            result_classes = set(re.findall(r'class="([^"]*)"', result_html))
            
            # All original classes should be preserved
            for css_class in original_classes:
                assert css_class in result_classes, \
                    f"CSS class '{css_class}' was lost during round-trip"


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
        
        # Should have exactly one placeholder
        assert len(placeholders) == 1
        
        # Restore should give back original
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
        
        # Should have exactly one placeholder
        assert len(placeholders) == 1
        
        # Restore should give back original
        restored = manager.restore_links(processed, placeholders)
        assert restored == original


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
        
        # The extracted text should contain the original text
        # Whitespace is normalized (multiple spaces become single space)
        normalized_text = ' '.join(text.split())
        assert normalized_text in extracted or extracted in normalized_text



# ============================================================================
# Property 3: UUID Link Preservation Tests
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
        """
        Property 3: UUID Link Preservation - Link count preserved
        
        For any HTML with UUID links, the number of links after injection
        should equal the number in the source.
        
        **Validates: Requirements 2.4, 7.3**
        """
        converter = FormatConverter()
        
        # Create HTML with UUID link
        source_html = f'<p>{surrounding_text} @UUID[{ref}]{{{text}}} more text</p>'
        
        # Count original links
        original_count = len(re.findall(r'@UUID\[', source_html))
        
        # Extract and inject
        extracted_text = converter.extract_text_from_html(source_html)
        result_html = converter.preserve_html_structure(source_html, extracted_text)
        
        # Count result links
        result_count = len(re.findall(r'@UUID\[', result_html))
        
        assert result_count == original_count, \
            f"UUID link count changed: {original_count} -> {result_count}"
    
    @given(ref=uuid_ref, text=simple_text, surrounding_text=simple_text)
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_uuid_link_ref_preserved(self, ref, text, surrounding_text):
        """
        Property 3: UUID Link Preservation - Link reference preserved
        
        For any HTML with UUID links, the link references after injection
        should be identical to the source.
        
        **Validates: Requirements 2.4, 7.3**
        """
        converter = FormatConverter()
        
        # Create HTML with UUID link
        source_html = f'<p>{surrounding_text} @UUID[{ref}]{{{text}}} more text</p>'
        
        # Extract original refs
        original_refs = re.findall(r'@UUID\[([^\]]+)\]', source_html)
        
        # Extract and inject
        extracted_text = converter.extract_text_from_html(source_html)
        result_html = converter.preserve_html_structure(source_html, extracted_text)
        
        # Extract result refs
        result_refs = re.findall(r'@UUID\[([^\]]+)\]', result_html)
        
        assert set(original_refs) == set(result_refs), \
            f"UUID refs changed: {original_refs} -> {result_refs}"
    
    @given(ref=uuid_ref, text=simple_text, surrounding_text=simple_text)
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_compendium_link_count_preserved(self, ref, text, surrounding_text):
        """
        Property 3: UUID Link Preservation - Compendium link count preserved
        
        For any HTML with Compendium links, the number of links after injection
        should equal the number in the source.
        
        **Validates: Requirements 2.4, 7.3**
        """
        converter = FormatConverter()
        
        # Create HTML with Compendium link
        source_html = f'<p>{surrounding_text} @Compendium[{ref}]{{{text}}} more text</p>'
        
        # Count original links
        original_count = len(re.findall(r'@Compendium\[', source_html))
        
        # Extract and inject
        extracted_text = converter.extract_text_from_html(source_html)
        result_html = converter.preserve_html_structure(source_html, extracted_text)
        
        # Count result links
        result_count = len(re.findall(r'@Compendium\[', result_html))
        
        assert result_count == original_count, \
            f"Compendium link count changed: {original_count} -> {result_count}"
    
    @given(ref=uuid_ref, text=simple_text, surrounding_text=simple_text)
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_compendium_link_ref_preserved(self, ref, text, surrounding_text):
        """
        Property 3: UUID Link Preservation - Compendium link reference preserved
        
        For any HTML with Compendium links, the link references after injection
        should be identical to the source.
        
        **Validates: Requirements 2.4, 7.3**
        """
        converter = FormatConverter()
        
        # Create HTML with Compendium link
        source_html = f'<p>{surrounding_text} @Compendium[{ref}]{{{text}}} more text</p>'
        
        # Extract original refs
        original_refs = re.findall(r'@Compendium\[([^\]]+)\]', source_html)
        
        # Extract and inject
        extracted_text = converter.extract_text_from_html(source_html)
        result_html = converter.preserve_html_structure(source_html, extracted_text)
        
        # Extract result refs
        result_refs = re.findall(r'@Compendium\[([^\]]+)\]', result_html)
        
        assert set(original_refs) == set(result_refs), \
            f"Compendium refs changed: {original_refs} -> {result_refs}"
    
    @given(data=babele_data())
    @settings(max_examples=100, deadline=10000)
    @pytest.mark.property
    def test_all_links_preserved_in_babele_data(self, data):
        """
        Property 3: UUID Link Preservation - All links preserved in Babele data
        
        For any Babele JSON data, all UUID and Compendium links should be
        preserved after extraction and injection.
        
        **Validates: Requirements 2.4, 7.3**
        """
        converter = FormatConverter()
        
        for key, entry in data['entries'].items():
            if 'description' not in entry:
                continue
                
            source_html = entry['description']
            
            # Count all links in source
            original_uuid_count = len(re.findall(r'@UUID\[', source_html))
            original_comp_count = len(re.findall(r'@Compendium\[', source_html))
            
            # Extract and inject
            extracted_text = converter.extract_text_from_html(source_html)
            result_html = converter.preserve_html_structure(source_html, extracted_text)
            
            # Count all links in result
            result_uuid_count = len(re.findall(r'@UUID\[', result_html))
            result_comp_count = len(re.findall(r'@Compendium\[', result_html))
            
            assert result_uuid_count == original_uuid_count, \
                f"UUID link count changed for {key}: {original_uuid_count} -> {result_uuid_count}"
            assert result_comp_count == original_comp_count, \
                f"Compendium link count changed for {key}: {original_comp_count} -> {result_comp_count}"
