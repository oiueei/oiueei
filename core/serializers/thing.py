"""
Thing serializers for OIUEEI.
"""

from rest_framework import serializers

from core.models import Thing
from core.utils import cloudinary_url
from core.validators import ImageIdField, SafeHeadlineField, validate_image_id


class ThingSerializer(serializers.ModelSerializer):
    """Full thing serializer."""

    thing_thumbnail_url = serializers.SerializerMethodField()
    thing_pictures_urls = serializers.SerializerMethodField()

    class Meta:
        model = Thing
        fields = [
            "thing_code",
            "thing_type",
            "thing_owner",
            "thing_created",
            "thing_headline",
            "thing_description",
            "thing_thumbnail",
            "thing_thumbnail_url",
            "thing_pictures",
            "thing_pictures_urls",
            "thing_status",
            "thing_faq",
            "thing_fee",
            "thing_deal",
            "thing_available",
        ]
        read_only_fields = [
            "thing_code",
            "thing_owner",
            "thing_created",
            "thing_faq",
            "thing_deal",
        ]

    def get_thing_thumbnail_url(self, obj):
        return cloudinary_url(obj.thing_thumbnail)

    def get_thing_pictures_urls(self, obj):
        return [cloudinary_url(pic_id) for pic_id in obj.thing_pictures if pic_id]


class ImageIdListField(serializers.ListField):
    """A list field that validates each item as an image ID."""

    child = serializers.CharField(max_length=16, allow_blank=True)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        return [validate_image_id(item) if item else item for item in value]


class ThingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a thing."""

    thing_headline = SafeHeadlineField(max_length=64)
    thing_thumbnail = ImageIdField()
    thing_pictures = ImageIdListField(required=False)

    class Meta:
        model = Thing
        fields = [
            "thing_type",
            "thing_headline",
            "thing_description",
            "thing_thumbnail",
            "thing_pictures",
            "thing_fee",
        ]


class ThingUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a thing."""

    thing_headline = SafeHeadlineField(max_length=64, required=False)
    thing_thumbnail = ImageIdField()
    thing_pictures = ImageIdListField(required=False)

    class Meta:
        model = Thing
        fields = [
            "thing_headline",
            "thing_description",
            "thing_thumbnail",
            "thing_pictures",
            "thing_status",
            "thing_fee",
            "thing_available",
        ]
