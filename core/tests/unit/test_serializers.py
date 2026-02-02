"""
Unit tests for OIUEEI serializers.
"""

import pytest

from core.models import FAQ, Collection, Thing, User
from core.serializers import (
    CollectionCreateSerializer,
    CollectionSerializer,
    FAQCreateSerializer,
    FAQSerializer,
    RequestLinkSerializer,
    ThingCreateSerializer,
    ThingSerializer,
    UserPublicSerializer,
    UserSerializer,
)


class TestRequestLinkSerializer:
    """Tests for RequestLinkSerializer."""

    def test_valid_email(self):
        """Should accept valid email."""
        serializer = RequestLinkSerializer(data={"email": "test@example.com"})
        assert serializer.is_valid()
        assert serializer.validated_data["email"] == "test@example.com"

    def test_invalid_email(self):
        """Should reject invalid email."""
        serializer = RequestLinkSerializer(data={"email": "not-an-email"})
        assert not serializer.is_valid()
        assert "email" in serializer.errors


@pytest.mark.django_db
class TestUserSerializer:
    """Tests for UserSerializer."""

    def test_serialize_user(self):
        """Should serialize user with all fields."""
        user = User.objects.create(
            user_code="ABC123",
            user_email="test@example.com",
            user_name="Test User",
            user_thumbnail="thumb123",
        )
        serializer = UserSerializer(user)
        data = serializer.data

        assert data["user_code"] == "ABC123"
        assert data["user_email"] == "test@example.com"
        assert data["user_name"] == "Test User"
        assert data["user_thumbnail_url"] is not None
        assert "cloudinary" in data["user_thumbnail_url"]


@pytest.mark.django_db
class TestUserPublicSerializer:
    """Tests for UserPublicSerializer."""

    def test_serialize_public_user(self):
        """Should serialize only public fields."""
        user = User.objects.create(
            user_code="ABC123",
            user_email="test@example.com",
            user_name="Test User",
        )
        serializer = UserPublicSerializer(user)
        data = serializer.data

        assert data["user_code"] == "ABC123"
        assert data["user_name"] == "Test User"
        assert "user_email" not in data


@pytest.mark.django_db
class TestCollectionSerializer:
    """Tests for CollectionSerializer."""

    def test_serialize_collection(self):
        """Should serialize collection with all fields."""
        collection = Collection.objects.create(
            collection_code="COLL01",
            collection_owner="ABC123",
            collection_headline="My Collection",
            collection_thumbnail="thumb123",
        )
        serializer = CollectionSerializer(collection)
        data = serializer.data

        assert data["collection_code"] == "COLL01"
        assert data["collection_headline"] == "My Collection"
        assert data["collection_thumbnail_url"] is not None


class TestCollectionCreateSerializer:
    """Tests for CollectionCreateSerializer."""

    def test_valid_collection(self):
        """Should accept valid collection data."""
        serializer = CollectionCreateSerializer(data={"collection_headline": "My Collection"})
        assert serializer.is_valid()

    def test_missing_headline(self):
        """Should reject missing headline."""
        serializer = CollectionCreateSerializer(data={})
        assert not serializer.is_valid()
        assert "collection_headline" in serializer.errors


@pytest.mark.django_db
class TestThingSerializer:
    """Tests for ThingSerializer."""

    def test_serialize_thing(self):
        """Should serialize thing with all fields."""
        thing = Thing.objects.create(
            thing_code="THNG01",
            thing_owner="ABC123",
            thing_headline="My Thing",
            thing_pictures=["pic1", "pic2"],
        )
        serializer = ThingSerializer(thing)
        data = serializer.data

        assert data["thing_code"] == "THNG01"
        assert data["thing_headline"] == "My Thing"
        assert len(data["thing_pictures_urls"]) == 2


class TestThingCreateSerializer:
    """Tests for ThingCreateSerializer."""

    def test_valid_thing(self):
        """Should accept valid thing data."""
        serializer = ThingCreateSerializer(
            data={
                "thing_headline": "My Thing",
                "thing_type": "GIFT_ARTICLE",
            }
        )
        assert serializer.is_valid()

    def test_missing_headline(self):
        """Should reject missing headline."""
        serializer = ThingCreateSerializer(data={"thing_type": "GIFT_ARTICLE"})
        assert not serializer.is_valid()


@pytest.mark.django_db
class TestFAQSerializer:
    """Tests for FAQSerializer."""

    def test_serialize_faq(self):
        """Should serialize FAQ with all fields."""
        faq = FAQ.objects.create(
            faq_code="FAQ001",
            faq_thing="THNG01",
            faq_questioner="USR001",
            faq_question="Is this available?",
            faq_answer="Yes!",
        )
        serializer = FAQSerializer(faq)
        data = serializer.data

        assert data["faq_code"] == "FAQ001"
        assert data["faq_question"] == "Is this available?"
        assert data["faq_answer"] == "Yes!"


class TestFAQCreateSerializer:
    """Tests for FAQCreateSerializer."""

    def test_valid_faq(self):
        """Should accept valid FAQ data."""
        serializer = FAQCreateSerializer(data={"faq_question": "Is this available?"})
        assert serializer.is_valid()

    def test_missing_question(self):
        """Should reject missing question."""
        serializer = FAQCreateSerializer(data={})
        assert not serializer.is_valid()
