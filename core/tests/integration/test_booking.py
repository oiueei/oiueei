"""
Integration tests for OIUEEI booking calendar system.
Tests for LEND_ARTICLE, RENT_ARTICLE, and SHARE_ARTICLE types.
"""

from datetime import date, timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Thing, User
from core.models.booking import BookingPeriod


@pytest.fixture
def lend_thing(db, user, collection):
    """Create a LEND_ARTICLE thing."""
    t = Thing.objects.create(
        thing_code="LEND01",
        thing_type="LEND_ARTICLE",
        thing_owner=user.user_code,
        thing_headline="Lend Item",
    )
    collection.add_thing(t.thing_code)
    return t


@pytest.fixture
def rent_thing(db, user, collection):
    """Create a RENT_ARTICLE thing with a fee."""
    t = Thing.objects.create(
        thing_code="RENT01",
        thing_type="RENT_ARTICLE",
        thing_owner=user.user_code,
        thing_headline="Rent Item",
        thing_fee=25.00,
    )
    collection.add_thing(t.thing_code)
    return t


@pytest.fixture
def share_thing(db, user, collection):
    """Create a SHARE_ARTICLE thing."""
    t = Thing.objects.create(
        thing_code="SHAR01",
        thing_type="SHARE_ARTICLE",
        thing_owner=user.user_code,
        thing_headline="Share Item",
    )
    collection.add_thing(t.thing_code)
    return t


def get_client_for_user(user):
    """Create an authenticated client for a user."""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.mark.django_db
class TestBookingCalendarView:
    """Tests for the thing calendar endpoint."""

    def test_guest_can_view_calendar(self, user, user2, lend_thing, collection):
        """Guest invited to collection can view calendar."""
        collection.add_invite(user2.user_code)

        client2 = get_client_for_user(user2)
        response = client2.get(f"/api/v1/things/{lend_thing.thing_code}/calendar/")

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)

    def test_owner_can_view_calendar(self, authenticated_client, lend_thing):
        """Owner can view their thing's calendar."""
        response = authenticated_client.get(f"/api/v1/things/{lend_thing.thing_code}/calendar/")

        assert response.status_code == status.HTTP_200_OK

    def test_non_invited_user_cannot_view_calendar(self, user, user2, lend_thing):
        """Non-invited user cannot view calendar."""
        client2 = get_client_for_user(user2)
        response = client2.get(f"/api/v1/things/{lend_thing.thing_code}/calendar/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_guest_sees_limited_calendar_info(self, user, user2, lend_thing, collection):
        """Guest sees only dates and status, not requester info."""
        collection.add_invite(user2.user_code)

        # Create a booking
        BookingPeriod.objects.create(
            thing_code=lend_thing.thing_code,
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3),
            status="ACCEPTED",
        )

        client2 = get_client_for_user(user2)
        response = client2.get(f"/api/v1/things/{lend_thing.thing_code}/calendar/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        # Guest should NOT see requester_code or booking_code
        assert "requester_code" not in response.data[0]
        assert "booking_code" not in response.data[0]
        # Guest should see dates and status
        assert "start_date" in response.data[0]
        assert "end_date" in response.data[0]
        assert "status" in response.data[0]

    def test_owner_sees_full_calendar_info(
        self, authenticated_client, user, user2, lend_thing, collection
    ):
        """Owner sees full details including requester info."""
        collection.add_invite(user2.user_code)

        BookingPeriod.objects.create(
            thing_code=lend_thing.thing_code,
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3),
            status="PENDING",
        )

        response = authenticated_client.get(f"/api/v1/things/{lend_thing.thing_code}/calendar/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        # Owner should see requester_code and booking_code
        assert "requester_code" in response.data[0]
        assert "booking_code" in response.data[0]


@pytest.mark.django_db
class TestBookingRequest:
    """Tests for booking request creation."""

    def test_guest_can_request_booking_for_lend(self, user, user2, lend_thing, collection):
        """Guest can request booking for LEND_ARTICLE with dates."""
        collection.add_invite(user2.user_code)

        client2 = get_client_for_user(user2)
        response = client2.post(
            f"/api/v1/things/{lend_thing.thing_code}/request/",
            {
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=3)),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Booking request sent"
        assert "booking_code" in response.data

    def test_guest_can_request_booking_for_rent(self, user, user2, rent_thing, collection):
        """Guest can request booking for RENT_ARTICLE (same as lend)."""
        collection.add_invite(user2.user_code)

        client2 = get_client_for_user(user2)
        response = client2.post(
            f"/api/v1/things/{rent_thing.thing_code}/request/",
            {
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=5)),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Booking request sent"

    def test_guest_can_request_booking_for_share(self, user, user2, share_thing, collection):
        """Guest can request booking for SHARE_ARTICLE."""
        collection.add_invite(user2.user_code)

        client2 = get_client_for_user(user2)
        response = client2.post(
            f"/api/v1/things/{share_thing.thing_code}/request/",
            {
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=1)),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Booking request sent"

    def test_owner_cannot_request_own_thing(self, authenticated_client, lend_thing):
        """Owner cannot request booking for their own thing."""
        response = authenticated_client.post(
            f"/api/v1/things/{lend_thing.thing_code}/request/",
            {
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=3)),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Cannot request your own thing"

    def test_non_invited_user_cannot_request_booking(self, user, user2, lend_thing):
        """Non-invited user cannot request booking."""
        client2 = get_client_for_user(user2)
        response = client2.post(
            f"/api/v1/things/{lend_thing.thing_code}/request/",
            {
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=3)),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_booking_requires_dates_for_lend(self, user, user2, lend_thing, collection):
        """LEND_ARTICLE requires start_date and end_date."""
        collection.add_invite(user2.user_code)

        client2 = get_client_for_user(user2)
        response = client2.post(
            f"/api/v1/things/{lend_thing.thing_code}/request/",
            {},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "start_date" in response.data
        assert "end_date" in response.data

    def test_start_date_must_be_today_or_future(self, user, user2, lend_thing, collection):
        """Start date cannot be in the past."""
        collection.add_invite(user2.user_code)

        client2 = get_client_for_user(user2)
        response = client2.post(
            f"/api/v1/things/{lend_thing.thing_code}/request/",
            {
                "start_date": str(date.today() - timedelta(days=1)),
                "end_date": str(date.today() + timedelta(days=3)),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_end_date_must_be_on_or_after_start_date(self, user, user2, lend_thing, collection):
        """End date must be >= start date."""
        collection.add_invite(user2.user_code)

        client2 = get_client_for_user(user2)
        response = client2.post(
            f"/api/v1/things/{lend_thing.thing_code}/request/",
            {
                "start_date": str(date.today() + timedelta(days=5)),
                "end_date": str(date.today()),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_same_day_booking_allowed(self, user, user2, lend_thing, collection):
        """Single day booking (start_date == end_date) is allowed."""
        collection.add_invite(user2.user_code)

        client2 = get_client_for_user(user2)
        today = date.today()
        response = client2.post(
            f"/api/v1/things/{lend_thing.thing_code}/request/",
            {
                "start_date": str(today),
                "end_date": str(today),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestBookingOverlap:
    """Tests for date overlap detection."""

    def test_cannot_book_overlapping_dates_with_pending(self, user, user2, lend_thing, collection):
        """Cannot book dates that overlap with PENDING booking."""
        collection.add_invite(user2.user_code)

        # Create a pending booking
        BookingPeriod.objects.create(
            thing_code=lend_thing.thing_code,
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=10),
            status="PENDING",
        )

        # Create a third user
        user3 = User.objects.create(
            user_code="TEST03",
            user_email="test3@example.com",
        )
        collection.add_invite(user3.user_code)

        # Try to book overlapping dates
        client3 = get_client_for_user(user3)
        response = client3.post(
            f"/api/v1/things/{lend_thing.thing_code}/request/",
            {
                "start_date": str(date.today() + timedelta(days=7)),
                "end_date": str(date.today() + timedelta(days=12)),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "overlap" in response.data["error"].lower()

    def test_cannot_book_overlapping_dates_with_accepted(self, user, user2, lend_thing, collection):
        """Cannot book dates that overlap with ACCEPTED booking."""
        collection.add_invite(user2.user_code)

        # Create an accepted booking
        BookingPeriod.objects.create(
            thing_code=lend_thing.thing_code,
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=10),
            status="ACCEPTED",
        )

        # Create a third user
        user3 = User.objects.create(
            user_code="TEST03",
            user_email="test3@example.com",
        )
        collection.add_invite(user3.user_code)

        # Try to book overlapping dates
        client3 = get_client_for_user(user3)
        response = client3.post(
            f"/api/v1/things/{lend_thing.thing_code}/request/",
            {
                "start_date": str(date.today() + timedelta(days=3)),
                "end_date": str(date.today() + timedelta(days=6)),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_can_book_non_overlapping_dates(self, user, user2, lend_thing, collection):
        """Can book dates that don't overlap."""
        collection.add_invite(user2.user_code)

        # Create an accepted booking
        BookingPeriod.objects.create(
            thing_code=lend_thing.thing_code,
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=10),
            status="ACCEPTED",
        )

        # Create a third user
        user3 = User.objects.create(
            user_code="TEST03",
            user_email="test3@example.com",
        )
        collection.add_invite(user3.user_code)

        # Book non-overlapping dates (after existing booking)
        client3 = get_client_for_user(user3)
        response = client3.post(
            f"/api/v1/things/{lend_thing.thing_code}/request/",
            {
                "start_date": str(date.today() + timedelta(days=11)),
                "end_date": str(date.today() + timedelta(days=15)),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

    def test_can_book_dates_with_rejected_booking(self, user, user2, lend_thing, collection):
        """Can book dates that overlap with REJECTED booking."""
        collection.add_invite(user2.user_code)

        # Create a rejected booking
        BookingPeriod.objects.create(
            thing_code=lend_thing.thing_code,
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=10),
            status="REJECTED",
        )

        # Create a third user
        user3 = User.objects.create(
            user_code="TEST03",
            user_email="test3@example.com",
        )
        collection.add_invite(user3.user_code)

        # Book overlapping dates (allowed since previous is rejected)
        client3 = get_client_for_user(user3)
        response = client3.post(
            f"/api/v1/things/{lend_thing.thing_code}/request/",
            {
                "start_date": str(date.today() + timedelta(days=5)),
                "end_date": str(date.today() + timedelta(days=10)),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestBookingAcceptReject:
    """Tests for booking accept/reject flow."""

    def test_accept_booking_via_link(self, api_client, user, user2, lend_thing):
        """Owner can accept booking via email link."""
        booking = BookingPeriod.objects.create(
            thing_code=lend_thing.thing_code,
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3),
        )

        response = api_client.get(f"/api/v1/bookings/{booking.booking_code}/accept/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Booking accepted"

        booking.refresh_from_db()
        assert booking.status == "ACCEPTED"

    def test_reject_booking_via_link(self, api_client, user, user2, lend_thing):
        """Owner can reject booking via email link."""
        booking = BookingPeriod.objects.create(
            thing_code=lend_thing.thing_code,
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3),
        )

        response = api_client.get(f"/api/v1/bookings/{booking.booking_code}/reject/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Booking rejected"

        booking.refresh_from_db()
        assert booking.status == "REJECTED"

    def test_cannot_accept_expired_booking(self, api_client, user, user2, lend_thing):
        """Cannot accept booking that has expired (72h)."""
        booking = BookingPeriod.objects.create(
            thing_code=lend_thing.thing_code,
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=15),
        )
        # Make it expired
        booking.booking_created = timezone.now() - timedelta(hours=100)
        booking.save()

        response = api_client.get(f"/api/v1/bookings/{booking.booking_code}/accept/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "expired" in response.data["error"].lower()

    def test_cannot_accept_already_accepted_booking(self, api_client, user, user2, lend_thing):
        """Cannot accept booking that's already accepted."""
        booking = BookingPeriod.objects.create(
            thing_code=lend_thing.thing_code,
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3),
            status="ACCEPTED",
        )

        response = api_client.get(f"/api/v1/bookings/{booking.booking_code}/accept/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_booking_not_found(self, api_client):
        """Should return 404 for non-existent booking."""
        response = api_client.get("/api/v1/bookings/NOEXST/accept/")

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestLendingThingStatusNotTaken:
    """Tests that LEND/RENT/SHARE things stay ACTIVE (not TAKEN)."""

    def test_lend_thing_stays_active_after_booking(self, user, user2, lend_thing, collection):
        """LEND_ARTICLE stays ACTIVE after booking request."""
        collection.add_invite(user2.user_code)

        client2 = get_client_for_user(user2)
        response = client2.post(
            f"/api/v1/things/{lend_thing.thing_code}/request/",
            {
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=3)),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

        lend_thing.refresh_from_db()
        assert lend_thing.thing_status == "ACTIVE"

    def test_rent_thing_stays_active_after_booking(self, user, user2, rent_thing, collection):
        """RENT_ARTICLE stays ACTIVE after booking request."""
        collection.add_invite(user2.user_code)

        client2 = get_client_for_user(user2)
        response = client2.post(
            f"/api/v1/things/{rent_thing.thing_code}/request/",
            {
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=3)),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

        rent_thing.refresh_from_db()
        assert rent_thing.thing_status == "ACTIVE"

    def test_thing_stays_active_after_booking_accepted(self, api_client, user, user2, lend_thing):
        """Thing stays ACTIVE even after booking is accepted."""
        booking = BookingPeriod.objects.create(
            thing_code=lend_thing.thing_code,
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3),
        )

        api_client.get(f"/api/v1/bookings/{booking.booking_code}/accept/")

        lend_thing.refresh_from_db()
        assert lend_thing.thing_status == "ACTIVE"

    def test_multiple_bookings_allowed_for_different_dates(
        self, user, user2, lend_thing, collection
    ):
        """Multiple non-overlapping bookings can exist for same thing."""
        collection.add_invite(user2.user_code)

        # Create first booking
        BookingPeriod.objects.create(
            thing_code=lend_thing.thing_code,
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3),
            status="ACCEPTED",
        )

        # Create third user for second booking
        user3 = User.objects.create(
            user_code="TEST03",
            user_email="test3@example.com",
        )
        collection.add_invite(user3.user_code)

        client3 = get_client_for_user(user3)
        response = client3.post(
            f"/api/v1/things/{lend_thing.thing_code}/request/",
            {
                "start_date": str(date.today() + timedelta(days=5)),
                "end_date": str(date.today() + timedelta(days=8)),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify 2 bookings exist
        bookings = BookingPeriod.objects.filter(thing_code=lend_thing.thing_code)
        assert bookings.count() == 2


@pytest.mark.django_db
class TestMyBookingsAndOwnerBookings:
    """Tests for my-bookings and owner-bookings endpoints."""

    def test_my_bookings_returns_user_requests(self, user, user2, lend_thing):
        """my-bookings returns bookings made by the user."""
        # Create booking by user2
        BookingPeriod.objects.create(
            thing_code=lend_thing.thing_code,
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3),
        )

        client2 = get_client_for_user(user2)
        response = client2.get("/api/v1/my-bookings/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["thing_code"] == lend_thing.thing_code

    def test_owner_bookings_returns_requests_for_owned_things(
        self, authenticated_client, user, user2, lend_thing
    ):
        """owner-bookings returns bookings for things owned by user."""
        # Create booking for user's thing
        BookingPeriod.objects.create(
            thing_code=lend_thing.thing_code,
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3),
        )

        response = authenticated_client.get("/api/v1/owner-bookings/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["requester_code"] == user2.user_code

    def test_my_bookings_empty_when_no_bookings(self, authenticated_client):
        """my-bookings returns empty list when user has no bookings."""
        response = authenticated_client.get("/api/v1/my-bookings/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data == []


@pytest.mark.django_db
class TestRentArticleWithFee:
    """Tests specific to RENT_ARTICLE with pricing."""

    def test_rent_thing_has_fee(self, rent_thing):
        """RENT_ARTICLE can have a fee."""
        assert rent_thing.thing_fee == 25.00

    def test_booking_rent_thing_works_same_as_lend(self, user, user2, rent_thing, collection):
        """Booking flow for RENT_ARTICLE is same as LEND_ARTICLE."""
        collection.add_invite(user2.user_code)

        client2 = get_client_for_user(user2)
        response = client2.post(
            f"/api/v1/things/{rent_thing.thing_code}/request/",
            {
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=5)),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

        # Fee calculation is done on frontend, not backend
        # Backend just stores the booking dates


@pytest.mark.django_db
class TestStandardReservationFlowUnchanged:
    """Tests that GIFT/SELL/ORDER flow is unchanged."""

    def test_gift_article_uses_standard_flow(self, user, user2, thing, collection):
        """GIFT_ARTICLE uses ReservationRequest flow, not BookingPeriod."""
        collection.add_invite(user2.user_code)

        client2 = get_client_for_user(user2)
        response = client2.post(f"/api/v1/things/{thing.thing_code}/request/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Reservation request sent"
        assert "reservation_code" in response.data
        # Should NOT have booking_code
        assert "booking_code" not in response.data

        # Thing status should be TAKEN for GIFT_ARTICLE
        thing.refresh_from_db()
        assert thing.thing_status == "TAKEN"
