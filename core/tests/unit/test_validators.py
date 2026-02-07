"""
Unit tests for OIUEEI validators.
"""

import pytest
from rest_framework import serializers

from core.validators import ImageIdField, SafeHeadlineField, validate_headline, validate_image_id


class TestValidateImageId:
    """Tests for validate_image_id function."""

    def test_valid_alphanumeric(self):
        """Should accept alphanumeric characters."""
        assert validate_image_id("abc123") == "abc123"
        assert validate_image_id("ABC123") == "ABC123"
        assert validate_image_id("ABCDEF") == "ABCDEF"
        assert validate_image_id("123456") == "123456"

    def test_valid_with_underscores(self):
        """Should accept underscores."""
        assert validate_image_id("abc_123") == "abc_123"
        assert validate_image_id("_test_") == "_test_"

    def test_valid_with_hyphens(self):
        """Should accept hyphens."""
        assert validate_image_id("abc-123") == "abc-123"
        assert validate_image_id("-test-") == "-test-"

    def test_valid_mixed(self):
        """Should accept mix of valid characters."""
        assert validate_image_id("abc_123-XYZ") == "abc_123-XYZ"

    def test_empty_value_allowed(self):
        """Should accept empty values."""
        assert validate_image_id("") == ""
        assert validate_image_id(None) is None

    def test_invalid_with_html(self):
        """Should reject HTML tags."""
        with pytest.raises(serializers.ValidationError):
            validate_image_id("<script>alert(1)</script>")

    def test_invalid_with_path_traversal(self):
        """Should reject path traversal attempts."""
        with pytest.raises(serializers.ValidationError):
            validate_image_id("../etc/passwd")
        with pytest.raises(serializers.ValidationError):
            validate_image_id("..\\windows\\system32")

    def test_invalid_with_spaces(self):
        """Should reject spaces."""
        with pytest.raises(serializers.ValidationError):
            validate_image_id("abc 123")

    def test_invalid_with_special_chars(self):
        """Should reject special characters."""
        with pytest.raises(serializers.ValidationError):
            validate_image_id("abc@123")
        with pytest.raises(serializers.ValidationError):
            validate_image_id("abc#123")
        with pytest.raises(serializers.ValidationError):
            validate_image_id("abc$123")


class TestImageIdField:
    """Tests for ImageIdField serializer field."""

    def test_valid_value(self):
        """Should accept valid image IDs."""
        field = ImageIdField()
        assert field.to_internal_value("abc123") == "abc123"

    def test_max_length_default(self):
        """Should have default max_length of 16."""
        field = ImageIdField()
        assert field.max_length == 16

    def test_not_required_by_default(self):
        """Should not be required by default."""
        field = ImageIdField()
        assert field.required is False

    def test_invalid_value_raises(self):
        """Should raise on invalid input."""
        field = ImageIdField()
        with pytest.raises(serializers.ValidationError):
            field.to_internal_value("<script>")


class TestValidateHeadline:
    """Tests for validate_headline function."""

    def test_valid_plain_text(self):
        """Should accept plain text."""
        assert validate_headline("Hello World") == "Hello World"
        assert validate_headline("My Collection 2024") == "My Collection 2024"

    def test_valid_with_punctuation(self):
        """Should accept punctuation."""
        assert validate_headline("Hello, World!") == "Hello, World!"
        assert validate_headline("What's up?") == "What's up?"

    def test_valid_with_unicode(self):
        """Should accept unicode characters."""
        assert validate_headline("Boda de Maria") == "Boda de Maria"

    def test_empty_value_allowed(self):
        """Should accept empty values."""
        assert validate_headline("") == ""
        assert validate_headline(None) is None

    def test_invalid_with_script_tags(self):
        """Should reject script tags."""
        with pytest.raises(serializers.ValidationError):
            validate_headline("<script>alert(1)</script>")

    def test_invalid_with_html_tags(self):
        """Should reject any HTML tags."""
        with pytest.raises(serializers.ValidationError):
            validate_headline("<b>Bold</b>")
        with pytest.raises(serializers.ValidationError):
            validate_headline("<a href='bad'>Link</a>")
        with pytest.raises(serializers.ValidationError):
            validate_headline("<img src=x onerror=alert(1)>")

    def test_invalid_with_event_handlers(self):
        """Should reject event handler attempts."""
        with pytest.raises(serializers.ValidationError):
            validate_headline('<div onmouseover="alert(1)">')


class TestSafeHeadlineField:
    """Tests for SafeHeadlineField serializer field."""

    def test_valid_value(self):
        """Should accept valid headlines."""
        field = SafeHeadlineField()
        assert field.to_internal_value("My Collection") == "My Collection"

    def test_invalid_value_raises(self):
        """Should raise on HTML input."""
        field = SafeHeadlineField()
        with pytest.raises(serializers.ValidationError):
            field.to_internal_value("<script>bad</script>")
