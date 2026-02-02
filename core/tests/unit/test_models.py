"""
Unit tests for OIUEEI models.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from core.models import FAQ, RSVP, Collection, Thing, User
from core.utils import cloudinary_url, generate_id


class TestGenerateId:
    """Tests for generate_id utility."""

    def test_generate_id_length(self):
        """ID should be 6 characters."""
        id_ = generate_id()
        assert len(id_) == 6

    def test_generate_id_uppercase(self):
        """ID should be uppercase alphanumeric."""
        id_ = generate_id()
        assert id_.isupper() or id_.isdigit() or all(c.isupper() or c.isdigit() for c in id_)

    def test_generate_id_unique(self):
        """IDs should be unique (statistically)."""
        ids = [generate_id() for _ in range(100)]
        assert len(set(ids)) == 100


class TestCloudinaryUrl:
    """Tests for cloudinary_url utility."""

    def test_cloudinary_url_with_id(self):
        """Should return valid Cloudinary URL."""
        url = cloudinary_url("abc123")
        assert "cloudinary.com" in url
        assert "abc123" in url
        assert url.endswith(".png")

    def test_cloudinary_url_without_id(self):
        """Should return None for empty ID."""
        assert cloudinary_url(None) is None
        assert cloudinary_url("") is None


@pytest.mark.django_db
class TestUserModel:
    """Tests for User model."""

    def test_create_user(self):
        """Should create a user with generated ID."""
        user = User.objects.create(user_email="test@example.com")
        assert len(user.user_code) == 6
        assert user.user_email == "test@example.com"
        assert user.is_active is True

    def test_user_str(self):
        """Should return readable string representation."""
        user = User.objects.create(
            user_code="ABC123",
            user_email="test@example.com",
        )
        assert "ABC123" in str(user)
        assert "test@example.com" in str(user)

    def test_user_collections_default(self):
        """User collections should default to empty lists."""
        user = User.objects.create(user_email="test@example.com")
        assert user.user_own_collections == []
        assert user.user_shared_collections == []
        assert user.user_things == []

    def test_update_last_activity(self):
        """Should update last activity date."""
        user = User.objects.create(user_email="test@example.com")
        old_date = user.user_last_activity
        user.update_last_activity()
        assert user.user_last_activity >= old_date


@pytest.mark.django_db
class TestRSVPModel:
    """Tests for RSVP model."""

    def test_create_rsvp(self):
        """Should create an RSVP with generated code."""
        rsvp = RSVP.objects.create(
            user_code="ABC123",
            user_email="test@example.com",
        )
        assert len(rsvp.rsvp_code) == 6
        assert rsvp.user_email == "test@example.com"

    def test_rsvp_is_valid(self):
        """New RSVP should be valid."""
        rsvp = RSVP.objects.create(
            user_code="ABC123",
            user_email="test@example.com",
        )
        assert rsvp.is_valid() is True

    def test_rsvp_expired(self):
        """Old RSVP should be invalid."""
        rsvp = RSVP.objects.create(
            user_code="ABC123",
            user_email="test@example.com",
        )
        rsvp.rsvp_created = timezone.now() - timedelta(hours=25)
        rsvp.save()
        assert rsvp.is_valid() is False


@pytest.mark.django_db
class TestCollectionModel:
    """Tests for Collection model."""

    def test_create_collection(self):
        """Should create a collection with generated code."""
        collection = Collection.objects.create(
            collection_owner="ABC123",
            collection_headline="My Collection",
        )
        assert len(collection.collection_code) == 6
        assert collection.collection_status == "ACTIVE"
        assert collection.collection_theeeme == "BAR_CEL_ONA"

    def test_add_thing(self):
        """Should add thing to collection."""
        collection = Collection.objects.create(
            collection_owner="ABC123",
            collection_headline="My Collection",
        )
        collection.add_thing("THNG01")
        assert "THNG01" in collection.collection_articles

    def test_remove_thing(self):
        """Should remove thing from collection."""
        collection = Collection.objects.create(
            collection_owner="ABC123",
            collection_headline="My Collection",
            collection_articles=["THNG01", "THNG02"],
        )
        collection.remove_thing("THNG01")
        assert "THNG01" not in collection.collection_articles
        assert "THNG02" in collection.collection_articles

    def test_add_invite(self):
        """Should add user to invites."""
        collection = Collection.objects.create(
            collection_owner="ABC123",
            collection_headline="My Collection",
        )
        collection.add_invite("USR001")
        assert "USR001" in collection.collection_invites

    def test_is_owner(self):
        """Should check ownership correctly."""
        collection = Collection.objects.create(
            collection_owner="ABC123",
            collection_headline="My Collection",
        )
        assert collection.is_owner("ABC123") is True
        assert collection.is_owner("XYZ789") is False

    def test_can_view(self):
        """Should check view permission correctly."""
        collection = Collection.objects.create(
            collection_owner="ABC123",
            collection_headline="My Collection",
            collection_invites=["USR001"],
        )
        assert collection.can_view("ABC123") is True  # Owner
        assert collection.can_view("USR001") is True  # Invited
        assert collection.can_view("XYZ789") is False  # Neither


@pytest.mark.django_db
class TestThingModel:
    """Tests for Thing model."""

    def test_create_thing(self):
        """Should create a thing with generated code."""
        thing = Thing.objects.create(
            thing_owner="ABC123",
            thing_headline="My Thing",
        )
        assert len(thing.thing_code) == 6
        assert thing.thing_type == "GIFT_ARTICLE"
        assert thing.thing_status == "ACTIVE"
        assert thing.thing_available is True

    def test_reserve(self):
        """Should reserve thing for user."""
        thing = Thing.objects.create(
            thing_owner="ABC123",
            thing_headline="My Thing",
        )
        thing.reserve("USR001")
        assert "USR001" in thing.thing_deal
        assert thing.thing_available is False

    def test_release(self):
        """Should release reservation."""
        thing = Thing.objects.create(
            thing_owner="ABC123",
            thing_headline="My Thing",
            thing_deal=["USR001"],
            thing_available=False,
        )
        thing.release("USR001")
        assert "USR001" not in thing.thing_deal
        assert thing.thing_available is True

    def test_add_faq(self):
        """Should add FAQ to thing."""
        thing = Thing.objects.create(
            thing_owner="ABC123",
            thing_headline="My Thing",
        )
        thing.add_faq("FAQ001")
        assert "FAQ001" in thing.thing_faq


@pytest.mark.django_db
class TestFAQModel:
    """Tests for FAQ model."""

    def test_create_faq(self):
        """Should create a FAQ with generated code."""
        faq = FAQ.objects.create(
            faq_thing="THNG01",
            faq_questioner="USR001",
            faq_question="Is this available?",
        )
        assert len(faq.faq_code) == 6
        assert faq.faq_is_visible is True
        assert faq.faq_answer == ""

    def test_has_answer(self):
        """Should check if answered correctly."""
        faq = FAQ.objects.create(
            faq_thing="THNG01",
            faq_questioner="USR001",
            faq_question="Is this available?",
        )
        assert faq.has_answer() is False
        faq.answer("Yes it is!")
        assert faq.has_answer() is True

    def test_answer(self):
        """Should set answer correctly."""
        faq = FAQ.objects.create(
            faq_thing="THNG01",
            faq_questioner="USR001",
            faq_question="Is this available?",
        )
        faq.answer("Yes it is!")
        assert faq.faq_answer == "Yes it is!"
