"""
User serializers for OIUEEI.
"""

from rest_framework import serializers

from core.models import User
from core.utils import cloudinary_url
from core.validators import ImageIdField, SafeHeadlineField


class UserSerializer(serializers.ModelSerializer):
    """Full user serializer for authenticated user."""

    user_thumbnail_url = serializers.SerializerMethodField()
    user_hero_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "user_code",
            "user_email",
            "user_name",
            "user_created",
            "user_last_activity",
            "user_own_collections",
            "user_invited_collections",
            "user_things",
            "user_headline",
            "user_thumbnail",
            "user_thumbnail_url",
            "user_hero",
            "user_hero_url",
        ]
        read_only_fields = [
            "user_code",
            "user_email",
            "user_created",
            "user_last_activity",
            "user_own_collections",
            "user_invited_collections",
            "user_things",
        ]

    def get_user_thumbnail_url(self, obj):
        return cloudinary_url(obj.user_thumbnail)

    def get_user_hero_url(self, obj):
        return cloudinary_url(obj.user_hero)


class UserPublicSerializer(serializers.ModelSerializer):
    """Public user profile serializer (limited fields)."""

    user_thumbnail_url = serializers.SerializerMethodField()
    user_hero_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "user_code",
            "user_name",
            "user_headline",
            "user_thumbnail",
            "user_thumbnail_url",
            "user_hero",
            "user_hero_url",
        ]

    def get_user_thumbnail_url(self, obj):
        return cloudinary_url(obj.user_thumbnail)

    def get_user_hero_url(self, obj):
        return cloudinary_url(obj.user_hero)


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""

    user_headline = SafeHeadlineField(max_length=64, required=False, allow_blank=True)
    user_thumbnail = ImageIdField()
    user_hero = ImageIdField()

    class Meta:
        model = User
        fields = [
            "user_name",
            "user_headline",
            "user_thumbnail",
            "user_hero",
        ]
