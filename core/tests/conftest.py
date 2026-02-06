"""
Pytest fixtures for OIUEEI tests.
"""

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import FAQ, RSVP, Collection, Theeeme, Thing, User


@pytest.fixture(autouse=True)
def default_theeeme(db):
    """Create the default theeeme for all tests."""
    theeeme, _ = Theeeme.objects.get_or_create(
        theeeme_code="JMPA01",
        defaults={
            "theeeme_name": "BAR_CEL_ONA",
            "theeeme_01": "FFCA2C",
            "theeeme_02": "CB4E22",
            "theeeme_03": "827F2A",
            "theeeme_04": "2B9A9E",
            "theeeme_05": "4F3B28",
            "theeeme_06": "FFF2EB",
        },
    )
    return theeeme


@pytest.fixture
def api_client():
    """Return an API client for testing."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create(
        user_code="TEST01",
        user_email="test@example.com",
        user_name="Test User",
    )


@pytest.fixture
def user2(db):
    """Create a second test user."""
    return User.objects.create(
        user_code="TEST02",
        user_email="test2@example.com",
        user_name="Test User 2",
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """Return an authenticated API client."""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def authenticated_client2(api_client, user2):
    """Return an authenticated API client for user2."""
    refresh = RefreshToken.for_user(user2)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def rsvp(db, user):
    """Create a test RSVP."""
    return RSVP.objects.create(
        rsvp_code="RSVP01",
        user_code=user.user_code,
        user_email=user.user_email,
    )


@pytest.fixture
def theeeme(default_theeeme):
    """Return the default theeeme for tests that explicitly need it."""
    return default_theeeme


@pytest.fixture
def collection(db, user, theeeme):
    """Create a test collection."""
    coll = Collection.objects.create(
        collection_code="COLL01",
        collection_owner=user.user_code,
        collection_headline="Test Collection",
        collection_theeeme=theeeme,
    )
    user.user_own_collections.append(coll.collection_code)
    user.save()
    return coll


@pytest.fixture
def thing(db, user, collection):
    """Create a test thing."""
    t = Thing.objects.create(
        thing_code="THNG01",
        thing_type="GIFT_THING",
        thing_owner=user.user_code,
        thing_headline="Test Thing",
    )
    user.user_things.append(t.thing_code)
    user.save()
    collection.add_thing(t.thing_code)
    return t


@pytest.fixture
def faq(db, user2, thing):
    """Create a test FAQ."""
    f = FAQ.objects.create(
        faq_code="FAQ001",
        faq_thing=thing.thing_code,
        faq_questioner=user2.user_code,
        faq_question="Is this available?",
    )
    thing.add_faq(f.faq_code)
    return f
