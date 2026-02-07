"""
Collection serializers for OIUEEI.
"""

from rest_framework import serializers

from core.models import Collection, Theeeme
from core.utils import cloudinary_url
from core.validators import ImageIdField, SafeHeadlineField


class CollectionSerializer(serializers.ModelSerializer):
    """Full collection serializer."""

    collection_thumbnail_url = serializers.SerializerMethodField()
    collection_hero_url = serializers.SerializerMethodField()
    collection_theeeme = serializers.SlugRelatedField(
        slug_field="theeeme_code",
        queryset=Theeeme.objects.all(),
    )

    class Meta:
        model = Collection
        fields = [
            "collection_code",
            "collection_owner",
            "collection_created",
            "collection_headline",
            "collection_description",
            "collection_thumbnail",
            "collection_thumbnail_url",
            "collection_hero",
            "collection_hero_url",
            "collection_status",
            "collection_things",
            "collection_invites",
            "collection_theeeme",
        ]
        read_only_fields = [
            "collection_code",
            "collection_owner",
            "collection_created",
            "collection_things",
            "collection_invites",
        ]

    def get_collection_thumbnail_url(self, obj):
        return cloudinary_url(obj.collection_thumbnail)

    def get_collection_hero_url(self, obj):
        return cloudinary_url(obj.collection_hero)


class CollectionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a collection."""

    collection_headline = SafeHeadlineField(max_length=64)
    collection_thumbnail = ImageIdField()
    collection_hero = ImageIdField()
    collection_theeeme = serializers.SlugRelatedField(
        slug_field="theeeme_code",
        queryset=Theeeme.objects.all(),
        required=False,
    )

    class Meta:
        model = Collection
        fields = [
            "collection_headline",
            "collection_description",
            "collection_thumbnail",
            "collection_hero",
            "collection_theeeme",
        ]


class CollectionUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a collection."""

    collection_headline = SafeHeadlineField(max_length=64, required=False)
    collection_thumbnail = ImageIdField()
    collection_hero = ImageIdField()
    collection_theeeme = serializers.SlugRelatedField(
        slug_field="theeeme_code",
        queryset=Theeeme.objects.all(),
        required=False,
    )

    class Meta:
        model = Collection
        fields = [
            "collection_headline",
            "collection_description",
            "collection_thumbnail",
            "collection_hero",
            "collection_status",
            "collection_theeeme",
        ]


class CollectionInviteSerializer(serializers.Serializer):
    """Serializer for inviting a user to a collection."""

    email = serializers.EmailField(max_length=64)


class CollectionAddThingSerializer(serializers.Serializer):
    """Serializer for adding a thing to a collection."""

    thing_code = serializers.CharField(max_length=6)


class CollectionRemoveInviteSerializer(serializers.Serializer):
    """Serializer for removing a user from a collection's invite list."""

    user_code = serializers.CharField(max_length=6)
