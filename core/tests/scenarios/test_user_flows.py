"""
Scenario tests for complete user flows in OIUEEI.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import RSVP, User


@pytest.mark.django_db
class TestMagicLinkFlow:
    """
    Scenario: Magic link authentication flow.
    1. User requests magic link
    2. User verifies magic link
    3. User gets session with JWT
    """

    def test_complete_magic_link_flow(self, api_client):
        """Test complete magic link authentication flow."""
        email = "newuser@example.com"

        # Step 1: Request magic link
        response = api_client.post(
            "/api/v1/auth/request-link/",
            {"email": email},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        # Verify user and RSVP were created
        user = User.objects.get(user_email=email)
        rsvp = RSVP.objects.get(user_code=user.user_code)

        # Step 2: Verify magic link
        response = api_client.get(f"/api/v1/auth/verify/{rsvp.rsvp_code}/")
        assert response.status_code == status.HTTP_200_OK
        assert "token" in response.data
        assert "refresh" in response.data
        assert response.data["user"]["user_code"] == user.user_code

        # Verify RSVP was deleted (one-time use)
        assert not RSVP.objects.filter(rsvp_code=rsvp.rsvp_code).exists()

        # Step 3: Use token to access protected endpoint
        token = response.data["token"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = api_client.get("/api/v1/auth/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["user_email"] == email


@pytest.mark.django_db
class TestCreateCollectionFlow:
    """
    Scenario: Create collection and add things.
    1. Login
    2. Create collection
    3. Add things to collection
    """

    def test_complete_create_collection_flow(self, authenticated_client, user):
        """Test complete collection creation flow."""
        # Step 1: Create collection
        response = authenticated_client.post(
            "/api/v1/collections/",
            {
                "collection_headline": "My Birthday Wishlist",
                "collection_description": "Things I want for my birthday",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        collection_code = response.data["collection_code"]

        # Step 2: Create thing and add to collection
        response = authenticated_client.post(
            "/api/v1/things/",
            {
                "thing_headline": "Red Bicycle",
                "thing_type": "GIFT_THING",
                "thing_description": "A shiny red bicycle",
                "collection_code": collection_code,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        thing_code = response.data["thing_code"]

        # Step 3: Verify thing is in collection
        response = authenticated_client.get(f"/api/v1/collections/{collection_code}/")
        assert response.status_code == status.HTTP_200_OK
        assert thing_code in response.data["collection_things"]

        # Step 4: Verify user's collections and things are updated
        response = authenticated_client.get("/api/v1/auth/me/")
        assert collection_code in response.data["user_own_collections"]
        assert thing_code in response.data["user_things"]


@pytest.mark.django_db
class TestShareCollectionFlow:
    """
    Scenario: Share collection with friend.
    1. Owner creates collection with things
    2. Owner invites friend
    3. Friend views collection
    4. Friend reserves thing
    """

    def test_complete_share_collection_flow(self):
        """Test complete collection sharing flow."""
        client = APIClient()

        # Create owner
        owner = User.objects.create(
            user_code="OWNER1",
            user_email="owner@example.com",
            user_name="Owner",
        )
        owner_token = RefreshToken.for_user(owner)

        # Create friend
        friend = User.objects.create(
            user_code="FRND01",
            user_email="friend@example.com",
            user_name="Friend",
        )
        friend_token = RefreshToken.for_user(friend)

        # Step 1: Owner creates collection
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {owner_token.access_token}")
        response = client.post(
            "/api/v1/collections/",
            {"collection_headline": "Gift Ideas"},
            format="json",
        )
        collection_code = response.data["collection_code"]

        # Step 2: Owner creates thing
        response = client.post(
            "/api/v1/things/",
            {
                "thing_headline": "Coffee Machine",
                "thing_type": "GIFT_THING",
                "collection_code": collection_code,
            },
            format="json",
        )
        thing_code = response.data["thing_code"]

        # Step 3: Owner invites friend
        response = client.post(
            f"/api/v1/collections/{collection_code}/invite/",
            {"email": "friend@example.com"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        # Step 3.5: Friend accepts invitation by verifying RSVP
        from core.models import RSVP

        rsvp = RSVP.objects.get(user_email="friend@example.com")
        response = client.get(f"/api/v1/auth/verify/{rsvp.rsvp_code}/")
        assert response.status_code == status.HTTP_200_OK

        # Step 4: Friend views shared collections
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {friend_token.access_token}")
        friend.refresh_from_db()

        response = client.get("/api/v1/invited-collections/")
        assert response.status_code == status.HTTP_200_OK
        assert any(c["collection_code"] == collection_code for c in response.data)

        # Step 5: Friend views collection
        response = client.get(f"/api/v1/collections/{collection_code}/")
        assert response.status_code == status.HTTP_200_OK
        assert thing_code in response.data["collection_things"]

        # Step 6: Friend requests thing (BookingPeriod flow)
        response = client.post(f"/api/v1/things/{thing_code}/request/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Booking request sent"
        booking_code = response.data["booking_code"]

        # Thing status should be TAKEN (awaiting owner approval)
        from core.models import Thing

        thing = Thing.objects.get(thing_code=thing_code)
        assert thing.thing_status == "TAKEN"

        # Step 7: Owner accepts the booking via RSVP
        # Find the accept RSVP
        accept_rsvp = RSVP.objects.get(
            rsvp_action="BOOKING_ACCEPT",
            rsvp_target_code=booking_code,
        )
        response = client.get(f"/api/v1/rsvp/{accept_rsvp.rsvp_code}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["action"] == "BOOKING_ACCEPT"

        # Step 8: Verify thing is now INACTIVE and friend is in thing_deal
        thing.refresh_from_db()
        assert thing.thing_status == "INACTIVE"
        assert thing.thing_available is False
        assert friend.user_code in thing.thing_deal


@pytest.mark.django_db
class TestFAQFlow:
    """
    Scenario: FAQ flow.
    1. Friend asks question about thing
    2. Owner answers question
    3. Question is visible to all
    """

    def test_complete_faq_flow(self):
        """Test complete FAQ flow."""
        client = APIClient()

        # Create owner
        owner = User.objects.create(
            user_code="OWNER2",
            user_email="owner2@example.com",
            user_name="Owner",
        )
        owner_token = RefreshToken.for_user(owner)

        # Create friend
        friend = User.objects.create(
            user_code="FRND02",
            user_email="friend2@example.com",
            user_name="Friend",
        )
        friend_token = RefreshToken.for_user(friend)

        # Owner creates collection and thing
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {owner_token.access_token}")
        response = client.post(
            "/api/v1/collections/",
            {"collection_headline": "For Sale"},
            format="json",
        )
        collection_code = response.data["collection_code"]

        response = client.post(
            "/api/v1/things/",
            {
                "thing_headline": "Vintage Camera",
                "thing_type": "SELL_THING",
                "thing_fee": "150.00",
                "collection_code": collection_code,
            },
            format="json",
        )
        thing_code = response.data["thing_code"]

        # Owner invites friend
        client.post(
            f"/api/v1/collections/{collection_code}/invite/",
            {"email": "friend2@example.com"},
            format="json",
        )

        # Friend accepts invitation by verifying RSVP
        rsvp = RSVP.objects.get(user_email="friend2@example.com")
        client.get(f"/api/v1/auth/verify/{rsvp.rsvp_code}/")

        # Step 1: Friend asks question
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {friend_token.access_token}")
        response = client.post(
            f"/api/v1/things/{thing_code}/faq/",
            {"faq_question": "Does it work with film?"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        faq_code = response.data["faq_code"]
        assert response.data["faq_answer"] == ""

        # Step 2: Owner answers question
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {owner_token.access_token}")
        response = client.post(
            f"/api/v1/faq/{faq_code}/answer/",
            {"faq_answer": "Yes, it works with 35mm film!"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["faq_answer"] == "Yes, it works with 35mm film!"

        # Step 3: Friend can see answered question
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {friend_token.access_token}")
        response = client.get(f"/api/v1/things/{thing_code}/faq/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["faq_answer"] == "Yes, it works with 35mm film!"


@pytest.mark.django_db
class TestCompleteUserJourney:
    """
    Scenario: Complete user journey from signup to transaction.
    """

    def test_complete_user_journey(self):
        """Test a complete user journey through the application."""
        client = APIClient()

        # === Alice signs up and creates a wishlist ===

        # Alice requests magic link
        response = client.post(
            "/api/v1/auth/request-link/",
            {"email": "alice@example.com"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        alice = User.objects.get(user_email="alice@example.com")
        alice_rsvp = RSVP.objects.get(user_code=alice.user_code)

        # Alice verifies and gets token
        response = client.get(f"/api/v1/auth/verify/{alice_rsvp.rsvp_code}/")
        alice_token = response.data["token"]

        # Alice updates profile
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {alice_token}")
        client.put(
            f"/api/v1/users/{alice.user_code}/",
            {"user_name": "Alice", "user_headline": "Birthday coming up!"},
            format="json",
        )

        # Alice creates birthday wishlist
        response = client.post(
            "/api/v1/collections/",
            {
                "collection_headline": "Alice's Birthday Wishlist",
                "collection_description": "Things I'd love for my birthday!",
            },
            format="json",
        )
        wishlist_code = response.data["collection_code"]

        # Alice adds items to wishlist
        items = [
            {"thing_headline": "Wireless Headphones", "thing_fee": "100.00"},
            {"thing_headline": "Cozy Blanket", "thing_fee": "50.00"},
            {"thing_headline": "Book: Clean Code", "thing_fee": "35.00"},
        ]

        thing_codes = []
        for item in items:
            response = client.post(
                "/api/v1/things/",
                {
                    **item,
                    "thing_type": "GIFT_THING",
                    "collection_code": wishlist_code,
                },
                format="json",
            )
            thing_codes.append(response.data["thing_code"])

        # === Alice invites Bob and Charlie ===

        response = client.post(
            f"/api/v1/collections/{wishlist_code}/invite/",
            {"email": "bob@example.com"},
            format="json",
        )
        bob = User.objects.get(user_email="bob@example.com")

        response = client.post(
            f"/api/v1/collections/{wishlist_code}/invite/",
            {"email": "charlie@example.com"},
            format="json",
        )
        charlie = User.objects.get(user_email="charlie@example.com")

        # === Bob and Charlie accept invitations ===

        bob_rsvp = RSVP.objects.get(user_email="bob@example.com")
        client.get(f"/api/v1/auth/verify/{bob_rsvp.rsvp_code}/")

        charlie_rsvp = RSVP.objects.get(user_email="charlie@example.com")
        client.get(f"/api/v1/auth/verify/{charlie_rsvp.rsvp_code}/")

        # === Bob logs in and requests an item ===

        bob_token = RefreshToken.for_user(bob)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {bob_token.access_token}")

        # Bob views shared collections
        response = client.get("/api/v1/invited-collections/")
        assert len(response.data) == 1

        # Bob requests headphones (BookingPeriod flow)
        response = client.post(f"/api/v1/things/{thing_codes[0]}/request/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Booking request sent"
        bob_booking_code = response.data["booking_code"]

        # Alice accepts Bob's request
        bob_accept_rsvp = RSVP.objects.get(
            rsvp_action="BOOKING_ACCEPT",
            rsvp_target_code=bob_booking_code,
        )
        client.get(f"/api/v1/rsvp/{bob_accept_rsvp.rsvp_code}/")

        # === Charlie asks a question ===

        charlie_token = RefreshToken.for_user(charlie)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {charlie_token.access_token}")

        # Charlie asks about the book
        response = client.post(
            f"/api/v1/things/{thing_codes[2]}/faq/",
            {"faq_question": "Is it the paperback or hardcover?"},
            format="json",
        )
        faq_code = response.data["faq_code"]

        # === Alice answers the question ===

        client.credentials(HTTP_AUTHORIZATION=f"Bearer {alice_token}")
        response = client.post(
            f"/api/v1/faq/{faq_code}/answer/",
            {"faq_answer": "Paperback is fine!"},
            format="json",
        )

        # === Charlie requests the book ===

        client.credentials(HTTP_AUTHORIZATION=f"Bearer {charlie_token.access_token}")
        response = client.post(f"/api/v1/things/{thing_codes[2]}/request/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Booking request sent"
        charlie_booking_code = response.data["booking_code"]

        # Alice accepts Charlie's request
        charlie_accept_rsvp = RSVP.objects.get(
            rsvp_action="BOOKING_ACCEPT",
            rsvp_target_code=charlie_booking_code,
        )
        client.get(f"/api/v1/rsvp/{charlie_accept_rsvp.rsvp_code}/")

        # === Final state verification ===

        client.credentials(HTTP_AUTHORIZATION=f"Bearer {alice_token}")

        # Alice sees her collection status
        response = client.get(f"/api/v1/collections/{wishlist_code}/")
        assert len(response.data["collection_things"]) == 3

        # Check reservations
        response = client.get(f"/api/v1/things/{thing_codes[0]}/")
        assert bob.user_code in response.data["thing_deal"]

        response = client.get(f"/api/v1/things/{thing_codes[2]}/")
        assert charlie.user_code in response.data["thing_deal"]

        # Blanket still available
        response = client.get(f"/api/v1/things/{thing_codes[1]}/")
        assert response.data["thing_available"] is True
