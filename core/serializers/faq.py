"""
FAQ serializers for OIUEEI.
"""

from rest_framework import serializers

from core.models import FAQ


class FAQSerializer(serializers.ModelSerializer):
    """Full FAQ serializer."""

    class Meta:
        model = FAQ
        fields = [
            "faq_code",
            "faq_thing",
            "faq_created",
            "faq_questioner",
            "faq_question",
            "faq_answer",
            "faq_is_visible",
        ]
        read_only_fields = [
            "faq_code",
            "faq_thing",
            "faq_created",
            "faq_questioner",
        ]


class FAQCreateSerializer(serializers.Serializer):
    """Serializer for creating a FAQ (asking a question)."""

    faq_question = serializers.CharField(max_length=64)


class FAQAnswerSerializer(serializers.Serializer):
    """Serializer for answering a FAQ."""

    faq_answer = serializers.CharField(max_length=256)
