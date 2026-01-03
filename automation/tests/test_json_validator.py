"""JSON Validator 属性测试

Property 8: JSON Validation Completeness
Validates: Requirements 6.1, 6.5
"""

import json
import pytest
from hypothesis import given, strategies as st, settings, assume
from pathlib import Path
import tempfile
import os

from automation.json_validator import JSONValidator, JSONValidationError, ValidationResult


# ============================================================================
# Strategies for generating test data
# ============================================================================

# Strategy for generating valid JSON values
json_value_strategy = st.recursive(
    st.none() | st.booleans() | st.integers() | st.floats(allow_nan=False, allow_infinity=False) | st.text(max_size=50),
    lambda children: st.lists(children, max_size=5) | st.dictionaries(
        st.text(min_size=1, max_size=20, alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            blacklist_characters='"\\/'
        )),
        children,
        max_size=5
    ),
    max_leaves=20
)

# Strategy for generating valid JSON objects (root must be object or array)
valid_json_strategy = st.dictionaries(
    st.text(min_size=1, max_size=20, alphabet=st.characters(
        whitelist_categories=('L', 'N'),
        blacklist_characters='"\\/'
    )),
    json_value_strategy,
    min_size=0,
    max_size=10
)

# Strategy for generating invalid JSON strings
invalid_json_mutations = st.sampled_from([
    ('missing_quote', lambda s: s.replace('"', '', 1) if '"' in s else '{invalid}'),
    ('missing_colon', lambda s: s.replace(':', '', 1) if ':' in s else '{key value}'),
    ('missing_comma', lambda s: s.replace(',', '', 1) if ',' in s else '{"a": 1 "b": 2}'),
    ('trailing_comma', lambda s: s.rstrip('}') + ',}' if s.endswith('}') else '{,}'),
    ('unclosed_brace', lambda s: s[:-1] if s.endswith('}') else '{'),
    ('unclosed_bracket', lambda s: s.replace(']', '', 1) if ']' in s else '[1, 2'),
    ('invalid_value', lambda s: s.replace('null', 'undefined', 1) if 'null' in s else '{"a": undefined}'),
])


# ============================================================================
# Property 8: JSON Validation Completeness Tests
# ============================================================================

class TestJSONValidationCompleteness:
    """JSON 验证完整性属性测试
    
    Property 8: JSON Validation Completeness
    Validates: Requirements 6.1, 6.5
    """
    
    @given(data=valid_json_strategy)
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_valid_json_passes_validation(self, data):
        """
        Property 8: JSON Validation Completeness
        
        *For any* valid JSON data, the validator SHALL report it as valid
        with no errors.
        
        Feature: translation-automation-workflow, Property 8: JSON Validation Completeness
        **Validates: Requirements 6.1, 6.5**
        """
        validator = JSONValidator()
        
        # Convert to JSON string
        json_string = json.dumps(data, ensure_ascii=False)
        
        # Validate
        result = validator.validate_string(json_string)
        
        # Should be valid
        assert result.is_valid, f"Valid JSON should pass validation: {json_string}"
        assert len(result.errors) == 0, f"Valid JSON should have no errors"
    
    @given(
        data=valid_json_strategy,
        mutation=invalid_json_mutations
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_invalid_json_detected_with_error_location(self, data, mutation):
        """
        Property 8: JSON Validation Completeness
        
        *For any* JSON file with syntax errors, the validator SHALL detect
        the error and report the line number and error type.
        
        Feature: translation-automation-workflow, Property 8: JSON Validation Completeness
        **Validates: Requirements 6.1, 6.5**
        """
        validator = JSONValidator()
        
        # Convert to JSON string and apply mutation
        json_string = json.dumps(data, ensure_ascii=False)
        mutation_name, mutation_func = mutation
        invalid_json = mutation_func(json_string)
        
        # Skip if mutation didn't actually make it invalid
        try:
            json.loads(invalid_json)
            # If we get here, the mutation didn't break the JSON
            assume(False)
        except json.JSONDecodeError:
            pass  # Good, it's invalid
        
        # Validate
        result = validator.validate_string(invalid_json)
        
        # Should be invalid
        assert not result.is_valid, f"Invalid JSON should fail validation: {invalid_json}"
        assert len(result.errors) > 0, f"Invalid JSON should have at least one error"
        
        # Error should have line and column information
        error = result.errors[0]
        assert error.line >= 1, f"Error should have valid line number (got {error.line})"
        assert error.column >= 1, f"Error should have valid column number (got {error.column})"
        assert len(error.message) > 0, f"Error should have a message"
    
    @given(data=valid_json_strategy)
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_file_validation_matches_string_validation(self, data):
        """
        Property: File validation should produce the same result as string validation.
        
        Feature: translation-automation-workflow, Property 8: JSON Validation Completeness
        **Validates: Requirements 6.1, 6.5**
        """
        validator = JSONValidator()
        
        # Convert to JSON string
        json_string = json.dumps(data, ensure_ascii=False, indent=2)
        
        # Validate as string
        string_result = validator.validate_string(json_string)
        
        # Write to temp file and validate
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.json', 
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(json_string)
            temp_path = f.name
        
        try:
            file_result = validator.validate_file(temp_path)
            
            # Results should match
            assert string_result.is_valid == file_result.is_valid, \
                "File and string validation should produce same validity result"
            assert len(string_result.errors) == len(file_result.errors), \
                "File and string validation should produce same number of errors"
        finally:
            os.unlink(temp_path)
    
    @given(
        num_valid_lines=st.integers(min_value=1, max_value=5),
        error_position=st.integers(min_value=0, max_value=5)
    )
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.property
    def test_error_line_number_accuracy(self, num_valid_lines, error_position):
        """
        Property: Error line numbers should accurately reflect the location of the error.
        
        Feature: translation-automation-workflow, Property 8: JSON Validation Completeness
        **Validates: Requirements 6.1, 6.5**
        """
        validator = JSONValidator()
        
        # Ensure error_position is within valid range (0 to num_valid_lines)
        actual_error_pos = min(error_position, num_valid_lines)
        
        # Build multi-line JSON with error at specific position
        # Line 1: {
        # Lines 2 to num_valid_lines+1: valid entries or error
        # Last line: }
        lines = ['{']
        
        for i in range(num_valid_lines + 1):  # +1 to include error position
            if i == actual_error_pos:
                # Insert error on this line
                lines.append('  "error_line": invalid_value,')
            elif i < num_valid_lines:
                lines.append(f'  "line_{i}": {i},')
        
        # Remove trailing comma from last line before closing brace
        if lines[-1].endswith(','):
            lines[-1] = lines[-1][:-1]
        lines.append('}')
        
        json_string = '\n'.join(lines)
        
        # Validate
        result = validator.validate_string(json_string)
        
        # Should be invalid
        assert not result.is_valid, f"JSON with invalid value should fail: {json_string}"
        assert len(result.errors) > 0, "Should have at least one error"
        
        # Error line should be close to where we inserted the error
        # (JSON parser may report slightly different line due to parsing strategy)
        error = result.errors[0]
        # The error should be on or near the line we made invalid
        # Line 1 is '{', so error at position 0 is on line 2
        expected_line = actual_error_pos + 2
        assert abs(error.line - expected_line) <= 1, \
            f"Error line {error.line} should be near expected line {expected_line}"


class TestJSONValidatorReportGeneration:
    """JSON 验证报告生成测试"""
    
    @given(
        valid_count=st.integers(min_value=0, max_value=5),
        invalid_count=st.integers(min_value=0, max_value=5)
    )
    @settings(max_examples=50, deadline=5000)
    @pytest.mark.property
    def test_report_summary_accuracy(self, valid_count, invalid_count):
        """
        Property: Report summary should accurately reflect validation results.
        
        Feature: translation-automation-workflow, Property 8: JSON Validation Completeness
        **Validates: Requirements 6.1, 6.5**
        """
        validator = JSONValidator()
        
        # Create mock results
        results = []
        for i in range(valid_count):
            results.append(ValidationResult(
                file_path=f"valid_{i}.json",
                is_valid=True,
                errors=[]
            ))
        for i in range(invalid_count):
            results.append(ValidationResult(
                file_path=f"invalid_{i}.json",
                is_valid=False,
                errors=[JSONValidationError(
                    file_path=f"invalid_{i}.json",
                    line=1,
                    column=1,
                    message="Test error",
                    error_type="syntax"
                )]
            ))
        
        # Generate JSON report
        report_json = validator.generate_report(results, format="json")
        report_data = json.loads(report_json)
        
        # Verify summary
        assert report_data["summary"]["total"] == valid_count + invalid_count
        assert report_data["summary"]["valid"] == valid_count
        assert report_data["summary"]["invalid"] == invalid_count
        assert len(report_data["results"]) == valid_count + invalid_count
