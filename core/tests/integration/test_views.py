"""
Integration tests for OIUEEI API views.
"""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestAuthViews:
    """Tests for authentication views."""

    def test_request_link_new_user(self, api_client):
        """Should create user and send magic link."""
        response = api_client.post(
            "/api/v1/auth/request-link/",
            {"email": "lala@oiueei.org"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "lala@oiueei.org"

    def test_request_link_existing_user(self, api_client, user):
        """Should send magic link for existing user."""
        response = api_client.post(
            "/api/v1/auth/request-link/",
            {"email": user.user_email},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == user.user_email

    def test_request_link_invalid_email(self, api_client):
        """Should reject invalid email."""
        response = api_client.post(
            "/api/v1/auth/request-link/",
            {"email": "not-an-email"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_verify_link_valid(self, api_client, rsvp, user):
        """Should verify valid RSVP and return token."""
        response = api_client.get(f"/api/v1/auth/verify/{rsvp.rsvp_code}/")
        assert response.status_code == status.HTTP_200_OK
        assert "token" in response.data
        assert "refresh" in response.data
        assert response.data["user"]["user_code"] == user.user_code

    def test_verify_link_invalid(self, api_client):
        """Should reject invalid RSVP code."""
        response = api_client.get("/api/v1/auth/verify/INVALID/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_authenticated(self, authenticated_client, user):
        """Should return current user."""
        response = authenticated_client.get("/api/v1/auth/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["user_code"] == user.user_code

    def test_me_unauthenticated(self, api_client):
        """Should reject unauthenticated request."""
        response = api_client.get("/api/v1/auth/me/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_authenticated(self, authenticated_client):
        """Should logout authenticated user."""
        response = authenticated_client.post("/api/v1/auth/logout/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Successfully logged out"

    def test_logout_unauthenticated(self, api_client):
        """Should reject logout for unauthenticated user."""
        response = api_client.post("/api/v1/auth/logout/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_with_refresh_token(self, authenticated_client, user):
        """Should logout and attempt to blacklist refresh token."""
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)
        response = authenticated_client.post(
            "/api/v1/auth/logout/",
            {"refresh": str(refresh)},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Successfully logged out"


@pytest.mark.django_db
class TestUserViews:
    """Tests for user views."""

    def test_get_own_profile(self, authenticated_client, user):
        """Should return full profile for own user."""
        response = authenticated_client.get(f"/api/v1/users/{user.user_code}/")
        assert response.status_code == status.HTTP_200_OK
        assert "user_email" in response.data

    def test_get_other_profile_denied_for_unrelated_user(self, authenticated_client, user2):
        """Should deny access to profile for unrelated user."""
        response = authenticated_client.get(f"/api/v1/users/{user2.user_code}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_other_profile_allowed_when_connected(
        self, authenticated_client, user, user2, collection
    ):
        """Should return public profile for connected user (invited to same collection)."""
        # Invite user2 to user's collection
        collection.add_invite(user2.user_code)

        response = authenticated_client.get(f"/api/v1/users/{user2.user_code}/")
        assert response.status_code == status.HTTP_200_OK
        assert "user_email" not in response.data

    def test_update_own_profile(self, authenticated_client, user):
        """Should update own profile."""
        response = authenticated_client.put(
            f"/api/v1/users/{user.user_code}/",
            {"user_name": "Lala"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["user_name"] == "Lala"

    def test_update_other_profile(self, authenticated_client, user2):
        """Should reject updating other user's profile."""
        response = authenticated_client.put(
            f"/api/v1/users/{user2.user_code}/",
            {"user_name": "Hacked"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestCollectionViews:
    """Tests for collection views."""

    def test_list_collections(self, authenticated_client, collection):
        """Should list user's collections."""
        response = authenticated_client.get("/api/v1/collections/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["collection_code"] == collection.collection_code

    def test_create_collection(self, authenticated_client, user):
        """Should create a new collection."""
        response = authenticated_client.post(
            "/api/v1/collections/",
            {"collection_headline": "New Collection"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["collection_headline"] == "New Collection"

    def test_get_collection(self, authenticated_client, collection):
        """Should get collection details."""
        response = authenticated_client.get(f"/api/v1/collections/{collection.collection_code}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["collection_headline"] == collection.collection_headline

    def test_update_collection(self, authenticated_client, collection):
        """Should update collection."""
        response = authenticated_client.put(
            f"/api/v1/collections/{collection.collection_code}/",
            {"collection_headline": "Updated Collection"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["collection_headline"] == "Updated Collection"

    def test_delete_collection(self, authenticated_client, collection):
        """Should delete collection."""
        response = authenticated_client.delete(f"/api/v1/collections/{collection.collection_code}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_invite_to_collection(self, authenticated_client, collection):
        """Should invite user to collection."""
        response = authenticated_client.post(
            f"/api/v1/collections/{collection.collection_code}/invite/",
            {"email": "lele@oiueei.org"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "lele@oiueei.org"

    def test_invite_to_collection_denied_for_non_owner(self, user, user2, collection):
        """Should deny invite for non-owner of collection."""
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken

        # user2 is NOT the owner of collection
        client2 = APIClient()
        refresh = RefreshToken.for_user(user2)
        client2.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        response = client2.post(
            f"/api/v1/collections/{collection.collection_code}/invite/",
            {"email": "someone@oiueei.org"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["error"] == "Only the owner can invite users"

    def test_invited_collections(self, authenticated_client, user, collection, user2):
        """Should list collections where user is invited."""
        # Add user to collection invites
        collection.add_invite(user.user_code)

        response = authenticated_client.get("/api/v1/invited-collections/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["collection_code"] == collection.collection_code

    def test_invite_creates_rsvp_with_collection_code(self, authenticated_client, collection):
        """Should create RSVP with collection_code when inviting."""
        from core.models import RSVP

        response = authenticated_client.post(
            f"/api/v1/collections/{collection.collection_code}/invite/",
            {"email": "newuser@oiueei.org"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        # Verify RSVP was created with collection_code
        rsvp = RSVP.objects.filter(user_email="newuser@oiueei.org").first()
        assert rsvp is not None
        assert rsvp.collection_code == collection.collection_code

    def test_invite_does_not_add_user_to_collection_immediately(
        self, authenticated_client, collection
    ):
        """User should NOT be in collection_invites until they accept."""
        from core.models import User

        response = authenticated_client.post(
            f"/api/v1/collections/{collection.collection_code}/invite/",
            {"email": "pending@oiueei.org"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        # User should NOT be in collection_invites yet
        invited_user = User.objects.get(user_email="pending@oiueei.org")
        collection.refresh_from_db()
        assert invited_user.user_code not in collection.collection_invites

    def test_verify_invite_link_adds_user_to_collection(self, api_client, collection):
        """Verifying invite RSVP should add user to collection."""
        from core.models import RSVP, User

        # Create a user and RSVP with collection_code
        invited_user = User.objects.create(
            user_code="INVTD1",
            user_email="invited@oiueei.org",
        )
        rsvp = RSVP.objects.create(
            user_code=invited_user.user_code,
            user_email=invited_user.user_email,
            collection_code=collection.collection_code,
        )

        # Verify the link
        response = api_client.get(f"/api/v1/auth/verify/{rsvp.rsvp_code}/")
        assert response.status_code == status.HTTP_200_OK

        # User should now be in collection_invites
        collection.refresh_from_db()
        invited_user.refresh_from_db()
        assert invited_user.user_code in collection.collection_invites
        assert collection.collection_code in invited_user.user_shared_collections

        # Response should include invited_collection
        assert response.data["invited_collection"] == collection.collection_code

    def test_remove_invite_from_collection(self, authenticated_client, user, user2, collection):
        """Should remove a user from collection invites."""
        # First add user2 to collection invites
        collection.add_invite(user2.user_code)
        user2.user_shared_collections.append(collection.collection_code)
        user2.save()

        response = authenticated_client.delete(
            f"/api/v1/collections/{collection.collection_code}/invite/",
            {"user_code": user2.user_code},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "User removed from collection"

        # Verify user was removed
        collection.refresh_from_db()
        user2.refresh_from_db()
        assert user2.user_code not in collection.collection_invites
        assert collection.collection_code not in user2.user_shared_collections

    def test_remove_invite_denied_for_non_owner(self, user, user2, collection):
        """Should deny removing invite for non-owner."""
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken

        collection.add_invite(user2.user_code)

        client2 = APIClient()
        refresh = RefreshToken.for_user(user2)
        client2.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        response = client2.delete(
            f"/api/v1/collections/{collection.collection_code}/invite/",
            {"user_code": user2.user_code},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["error"] == "Only the owner can remove invites"

    def test_remove_invite_user_not_invited(self, authenticated_client, user2, collection):
        """Should return error when user is not invited."""
        response = authenticated_client.delete(
            f"/api/v1/collections/{collection.collection_code}/invite/",
            {"user_code": user2.user_code},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "User is not invited to this collection"

    def test_add_thing_to_collection(self, authenticated_client, user, collection):
        """Should add an existing thing to a collection."""
        from core.models import Thing

        # Create a thing not in any collection
        thing = Thing.objects.create(
            thing_code="THING2",
            thing_owner=user.user_code,
            thing_headline="New Thing",
            thing_type="GIFT_ARTICLE",
        )

        response = authenticated_client.post(
            f"/api/v1/collections/{collection.collection_code}/",
            {"thing_code": thing.thing_code},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Thing added to collection"
        assert thing.thing_code in response.data["collection"]["collection_articles"]

    def test_add_thing_to_collection_denied_for_non_owner(self, user, user2, collection):
        """Should deny adding thing for non-owner of collection."""
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken

        from core.models import Thing

        # Create thing owned by user2
        thing = Thing.objects.create(
            thing_code="THING2",
            thing_owner=user2.user_code,
            thing_headline="User2 Thing",
            thing_type="GIFT_ARTICLE",
        )

        # user2 tries to add to user's collection
        client2 = APIClient()
        refresh = RefreshToken.for_user(user2)
        client2.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        response = client2.post(
            f"/api/v1/collections/{collection.collection_code}/",
            {"thing_code": thing.thing_code},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["error"] == "Only the owner can add things to this collection"

    def test_add_other_users_thing_to_collection_denied(
        self, authenticated_client, user, user2, collection
    ):
        """Should deny adding another user's thing to collection."""
        from core.models import Thing

        # Create thing owned by user2
        thing = Thing.objects.create(
            thing_code="THING2",
            thing_owner=user2.user_code,
            thing_headline="User2 Thing",
            thing_type="GIFT_ARTICLE",
        )

        # user (owner of collection) tries to add user2's thing
        response = authenticated_client.post(
            f"/api/v1/collections/{collection.collection_code}/",
            {"thing_code": thing.thing_code},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["error"] == "You can only add your own things to collections"

    def test_add_thing_already_in_collection(self, authenticated_client, thing, collection):
        """Should return error when thing is already in collection."""
        response = authenticated_client.post(
            f"/api/v1/collections/{collection.collection_code}/",
            {"thing_code": thing.thing_code},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Thing is already in this collection"

    def test_add_nonexistent_thing_to_collection(self, authenticated_client, collection):
        """Should return 404 for nonexistent thing."""
        response = authenticated_client.post(
            f"/api/v1/collections/{collection.collection_code}/",
            {"thing_code": "NOEXST"},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["error"] == "Thing not found"

    def test_add_thing_to_nonexistent_collection(self, authenticated_client, user):
        """Should return 404 for nonexistent collection."""
        from core.models import Thing

        thing = Thing.objects.create(
            thing_code="THING2",
            thing_owner=user.user_code,
            thing_headline="New Thing",
            thing_type="GIFT_ARTICLE",
        )

        response = authenticated_client.post(
            "/api/v1/collections/NOEXST/",
            {"thing_code": thing.thing_code},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["error"] == "Collection not found"


@pytest.mark.django_db
class TestThingViews:
    """Tests for thing views."""

    def test_list_things(self, authenticated_client, thing):
        """Should list user's things."""
        response = authenticated_client.get("/api/v1/things/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_create_thing(self, authenticated_client):
        """Should create a new thing."""
        response = authenticated_client.post(
            "/api/v1/things/",
            {
                "thing_headline": "New Thing",
                "thing_type": "GIFT_ARTICLE",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["thing_headline"] == "New Thing"

    def test_get_thing(self, authenticated_client, thing):
        """Should get thing details."""
        response = authenticated_client.get(f"/api/v1/things/{thing.thing_code}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["thing_headline"] == thing.thing_headline

    def test_update_thing(self, authenticated_client, thing):
        """Should update thing."""
        response = authenticated_client.put(
            f"/api/v1/things/{thing.thing_code}/",
            {"thing_headline": "Updated Thing"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["thing_headline"] == "Updated Thing"

    def test_delete_thing(self, authenticated_client, thing):
        """Should delete thing."""
        response = authenticated_client.delete(f"/api/v1/things/{thing.thing_code}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_reserve_thing(self, authenticated_client, user, user2, thing, collection):
        """Should reserve thing."""
        # Share collection with user2 first
        collection.add_invite(user2.user_code)
        user2.user_shared_collections.append(collection.collection_code)
        user2.save()

        # Create new client for user2
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken

        client2 = APIClient()
        refresh = RefreshToken.for_user(user2)
        client2.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        response = client2.post(f"/api/v1/things/{thing.thing_code}/reserve/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["thing"]["thing_available"] is False

    def test_cannot_reserve_own_thing(self, authenticated_client, thing):
        """Should not reserve own thing."""
        response = authenticated_client.post(f"/api/v1/things/{thing.thing_code}/reserve/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestFAQViews:
    """Tests for FAQ views."""

    def test_list_faqs(self, authenticated_client, thing, faq):
        """Should list FAQs for a thing."""
        response = authenticated_client.get(f"/api/v1/things/{thing.thing_code}/faq/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_create_faq(self, authenticated_client, thing):
        """Should create a new FAQ."""
        response = authenticated_client.post(
            f"/api/v1/things/{thing.thing_code}/faq/",
            {"faq_question": "How big is it?"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["faq_question"] == "How big is it?"

    def test_get_faq(self, authenticated_client, faq):
        """Should get FAQ details."""
        response = authenticated_client.get(f"/api/v1/faq/{faq.faq_code}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["faq_question"] == faq.faq_question

    def test_answer_faq(self, authenticated_client, faq):
        """Should answer FAQ as thing owner."""
        response = authenticated_client.post(
            f"/api/v1/faq/{faq.faq_code}/answer/",
            {"faq_answer": "It's not very big!"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["faq_answer"] == "It's not very big!"

    def test_answer_faq_denied_for_non_owner(self, user, user2, faq):
        """Should deny answering FAQ for non-owner of the thing."""
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken

        # user2 is the questioner but NOT the thing owner
        client2 = APIClient()
        refresh = RefreshToken.for_user(user2)
        client2.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        response = client2.post(
            f"/api/v1/faq/{faq.faq_code}/answer/",
            {"faq_answer": "I shouldn't be able to answer this!"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["error"] == "Only the thing owner can answer questions"


@pytest.mark.django_db
class TestSecurityRestrictions:
    """Tests for security restrictions on resource access."""

    def _get_client_for_user(self, user):
        """Create an authenticated client for a user."""
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken

        client = APIClient()
        refresh = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return client

    # Collection access tests

    def test_collection_access_denied_for_non_invited_user(
        self, authenticated_client, user, user2, collection
    ):
        """Should deny access to collection for non-invited user."""
        client2 = self._get_client_for_user(user2)
        response = client2.get(f"/api/v1/collections/{collection.collection_code}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_collection_access_allowed_for_owner(self, authenticated_client, collection):
        """Should allow owner to view their collection."""
        response = authenticated_client.get(f"/api/v1/collections/{collection.collection_code}/")
        assert response.status_code == status.HTTP_200_OK

    def test_collection_access_allowed_for_invited_user(self, user, user2, collection):
        """Should allow invited user to view collection."""
        # Invite user2
        collection.add_invite(user2.user_code)

        client2 = self._get_client_for_user(user2)
        response = client2.get(f"/api/v1/collections/{collection.collection_code}/")
        assert response.status_code == status.HTTP_200_OK

    # Invited collections endpoint tests

    def test_invited_collections_empty_when_no_invites(self, authenticated_client):
        """Should return empty list when user has no invites."""
        response = authenticated_client.get("/api/v1/invited-collections/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_invited_collections_returns_invited(self, user, user2, collection):
        """Should return collections user is invited to."""
        # Invite user2
        collection.add_invite(user2.user_code)

        client2 = self._get_client_for_user(user2)
        response = client2.get("/api/v1/invited-collections/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["collection_code"] == collection.collection_code

    # Thing access tests

    def test_thing_access_denied_for_non_invited_user(self, user, user2, thing):
        """Should deny access to thing for non-invited user."""
        client2 = self._get_client_for_user(user2)
        response = client2.get(f"/api/v1/things/{thing.thing_code}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_thing_access_allowed_for_owner(self, authenticated_client, thing):
        """Should allow owner to view their thing."""
        response = authenticated_client.get(f"/api/v1/things/{thing.thing_code}/")
        assert response.status_code == status.HTTP_200_OK

    def test_thing_access_allowed_for_invited_user(self, user, user2, thing, collection):
        """Should allow invited user to view thing in collection."""
        # Invite user2 to collection that contains the thing
        collection.add_invite(user2.user_code)

        client2 = self._get_client_for_user(user2)
        response = client2.get(f"/api/v1/things/{thing.thing_code}/")
        assert response.status_code == status.HTTP_200_OK

    # Invited things endpoint tests

    def test_invited_things_empty_when_no_invites(self, authenticated_client):
        """Should return empty list when user has no invites."""
        response = authenticated_client.get("/api/v1/invited-things/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_invited_things_returns_invited(self, user, user2, thing, collection):
        """Should return things from collections user is invited to."""
        # Invite user2
        collection.add_invite(user2.user_code)

        client2 = self._get_client_for_user(user2)
        response = client2.get("/api/v1/invited-things/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["thing_code"] == thing.thing_code

    # FAQ access tests

    def test_faq_list_denied_for_non_invited_user(self, user, user2, thing):
        """Should deny FAQ list for non-invited user."""
        client2 = self._get_client_for_user(user2)
        response = client2.get(f"/api/v1/things/{thing.thing_code}/faq/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_faq_list_allowed_for_invited_user(self, user, user2, thing, collection, faq):
        """Should allow FAQ list for invited user."""
        collection.add_invite(user2.user_code)

        client2 = self._get_client_for_user(user2)
        response = client2.get(f"/api/v1/things/{thing.thing_code}/faq/")
        assert response.status_code == status.HTTP_200_OK

    def test_faq_detail_denied_for_non_invited_user(self, user, user2, faq, thing):
        """Should deny FAQ detail for non-invited user."""
        # Make FAQ visible first
        faq.faq_is_visible = True
        faq.save()

        # Create a third user (not owner, not questioner, not invited)
        from core.models import User

        user3 = User.objects.create(
            user_code="TEST03",
            user_email="test3@example.com",
            user_name="Test User 3",
        )

        client3 = self._get_client_for_user(user3)
        response = client3.get(f"/api/v1/faq/{faq.faq_code}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_faq_create_denied_for_non_invited_user(self, user, user2, thing):
        """Should deny FAQ creation for non-invited user."""
        # Create a third user
        from core.models import User

        user3 = User.objects.create(
            user_code="TEST03",
            user_email="test3@example.com",
            user_name="Test User 3",
        )

        client3 = self._get_client_for_user(user3)
        response = client3.post(
            f"/api/v1/things/{thing.thing_code}/faq/",
            {"faq_question": "Is this available?"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # User profile access tests

    def test_user_profile_access_denied_for_unrelated_user(self, user, user2):
        """Should deny profile access for unrelated user."""
        client2 = self._get_client_for_user(user2)
        response = client2.get(f"/api/v1/users/{user.user_code}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_user_profile_access_allowed_for_self(self, authenticated_client, user):
        """Should allow viewing own profile."""
        response = authenticated_client.get(f"/api/v1/users/{user.user_code}/")
        assert response.status_code == status.HTTP_200_OK

    def test_user_profile_access_allowed_when_invited_to_their_collection(
        self, user, user2, collection
    ):
        """Should allow profile access when invited to their collection."""
        # User invites user2 to their collection
        collection.add_invite(user2.user_code)

        # User2 can now see user's profile (owner of collection they're invited to)
        client2 = self._get_client_for_user(user2)
        response = client2.get(f"/api/v1/users/{user.user_code}/")
        assert response.status_code == status.HTTP_200_OK

    def test_user_profile_access_allowed_when_they_invited_to_your_collection(
        self, user, user2, theeeme
    ):
        """Should allow profile access when user is in your collection_invites."""
        from core.models import Collection

        # User2 creates a collection and invites user
        coll2 = Collection.objects.create(
            collection_code="COLL02",
            collection_owner=user2.user_code,
            collection_headline="User2 Collection",
            collection_theeeme=theeeme,
        )
        coll2.add_invite(user.user_code)

        # User can now see user2's profile (they invited me)
        client1 = self._get_client_for_user(user)
        response = client1.get(f"/api/v1/users/{user2.user_code}/")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestReservationViews:
    """Tests for reservation request flow."""

    def _get_client_for_user(self, user):
        """Create an authenticated client for a user."""
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken

        client = APIClient()
        refresh = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return client

    def test_request_reservation(self, user, user2, thing, collection):
        """Should create a reservation request and change thing status to TAKEN."""
        # Invite user2 to collection
        collection.add_invite(user2.user_code)

        client2 = self._get_client_for_user(user2)
        response = client2.post(f"/api/v1/things/{thing.thing_code}/request/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Reservation request sent"
        assert "reservation_code" in response.data

        # Verify thing status changed to TAKEN
        thing.refresh_from_db()
        assert thing.thing_status == "TAKEN"

    def test_request_reservation_denied_for_owner(self, authenticated_client, thing):
        """Should deny owner from requesting their own thing."""
        response = authenticated_client.post(f"/api/v1/things/{thing.thing_code}/request/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Cannot request your own thing"

    def test_request_reservation_denied_for_non_invited(self, user, user2, thing):
        """Should deny non-invited user from requesting."""
        client2 = self._get_client_for_user(user2)
        response = client2.post(f"/api/v1/things/{thing.thing_code}/request/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_request_reservation_denied_for_non_active_thing(self, user, user2, thing, collection):
        """Should deny request for non-active thing."""
        collection.add_invite(user2.user_code)
        thing.thing_status = "TAKEN"
        thing.save()

        client2 = self._get_client_for_user(user2)
        response = client2.post(f"/api/v1/things/{thing.thing_code}/request/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Thing is not available for reservation"

    def test_accept_reservation(self, api_client, user, user2, thing, collection):
        """Should accept reservation and change thing status to INACTIVE."""
        from core.models import ReservationRequest

        collection.add_invite(user2.user_code)

        # Create reservation request
        reservation = ReservationRequest.objects.create(
            thing_code=thing.thing_code,
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
        )
        thing.thing_status = "TAKEN"
        thing.save()

        # Accept via link
        response = api_client.get(f"/api/v1/reservations/{reservation.reservation_code}/accept/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Reservation accepted"

        # Verify thing status and reservation status
        thing.refresh_from_db()
        reservation.refresh_from_db()
        assert thing.thing_status == "INACTIVE"
        assert thing.thing_available is False
        assert user2.user_code in thing.thing_deal
        assert reservation.status == "ACCEPTED"

    def test_reject_reservation(self, api_client, user, user2, thing, collection):
        """Should reject reservation and change thing status back to ACTIVE."""
        from core.models import ReservationRequest

        collection.add_invite(user2.user_code)

        # Create reservation request
        reservation = ReservationRequest.objects.create(
            thing_code=thing.thing_code,
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
        )
        thing.thing_status = "TAKEN"
        thing.save()

        # Reject via link
        response = api_client.get(f"/api/v1/reservations/{reservation.reservation_code}/reject/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Reservation rejected"

        # Verify thing status and reservation status
        thing.refresh_from_db()
        reservation.refresh_from_db()
        assert thing.thing_status == "ACTIVE"
        assert reservation.status == "REJECTED"

    def test_reservation_expired(self, api_client, user, user2, thing):
        """Should return error for expired reservation."""
        from datetime import timedelta

        from django.utils import timezone

        from core.models import ReservationRequest

        # Create expired reservation
        reservation = ReservationRequest.objects.create(
            thing_code=thing.thing_code,
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
        )
        reservation.reservation_created = timezone.now() - timedelta(hours=100)
        reservation.save()

        response = api_client.get(f"/api/v1/reservations/{reservation.reservation_code}/accept/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Reservation expired or already processed"

    def test_duplicate_request_denied(self, user, user2, thing, collection):
        """Should deny duplicate pending request."""
        from core.models import ReservationRequest

        collection.add_invite(user2.user_code)

        # Create existing pending request
        ReservationRequest.objects.create(
            thing_code=thing.thing_code,
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
            status="PENDING",
        )

        client2 = self._get_client_for_user(user2)
        response = client2.post(f"/api/v1/things/{thing.thing_code}/request/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "You already have a pending request for this thing"
