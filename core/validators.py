"""
Custom validators and fields for OIUEEI.

Provides secure validation for user inputs including:
- Image IDs (alphanumeric only)
- Headlines (no HTML/XSS)
"""

import re

import bleach
from rest_framework import serializers


def validate_image_id(value):
    """
    Validate that an image ID contains only safe characters.

    Only allows letters, numbers, underscores, and hyphens.
    This prevents path traversal and injection attacks.
    """
    if value and not re.match(r"^[a-zA-Z0-9_-]+$", value):
        raise serializers.ValidationError(
            "Image ID can only contain letters, numbers, underscores, and hyphens."
        )
    return value


class ImageIdField(serializers.CharField):
    """
    A CharField that validates image IDs to be alphanumeric only.

    Prevents injection attacks through Cloudinary image IDs.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("max_length", 16)
        kwargs.setdefault("required", False)
        kwargs.setdefault("allow_blank", True)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        return validate_image_id(value)


def validate_headline(value):
    """
    Validate that a headline does not contain HTML tags.

    Rejects any input that contains HTML to prevent XSS attacks.
    """
    if value:
        sanitized = bleach.clean(value, tags=[], strip=True)
        if sanitized != value:
            raise serializers.ValidationError("HTML tags are not allowed.")
    return value


class SafeHeadlineField(serializers.CharField):
    """
    A CharField that rejects HTML content to prevent XSS.

    Uses bleach to detect and reject any HTML tags in the input.
    """

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        return validate_headline(value)
