"""
Integration tests for OIUEEI booking calendar system.
Tests for LEND_THING, RENT_THING, and SHARE_THING types.
"""

from datetime import date, timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import RSVP, Thing, User
from core.models.booking import BookingPeriod


@pytest.fixture
def lend_thing(db, user, collection):
    """Create a LEND_THING thing."""
    t = Thing.objects.create(
        thing_code="LEND01",
        thing_type="LEND_THING",
        thing_owner=user.user_code,
        thing_headline="Lend Item",
    )
    collection.add_thing(t.thing_code)
    return t


@pytest.fixture
def rent_thing(db, user, collection):
    """Create a RENT_THING thing with a fee."""
    t = Thing.objects.create(
        thing_code="RENT01",
        thing_type="RENT_THING",
        thing_owner=user.user_code,
        thing_headline="Rent Item",
        thing_fee=25.00,
    )
    collection.add_thing(t.thing_code)
    return t


@pytest.fixture
def share_thing(db, user, collection):
    """Create a SHARE_THING thing."""
    t = Thing.objects.create(
        thing_code="SHAR01",
        thing_type="SHARE_THING",
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
        """Guest can request booking for LEND_THING with dates."""
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
        """Guest can request booking for RENT_THING (same as lend)."""
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
        """Guest can request booking for SHARE_THING."""
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
        """LEND_THING requires start_date and end_date."""
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
    """Tests for booking accept/reject flow via RSVP."""

    def test_accept_booking_via_link(self, api_client, user, user2, lend_thing):
        """Owner can accept booking via RSVP email link."""
        booking = BookingPeriod.objects.create(
            thing_code=lend_thing.thing_code,
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3),
        )

        # Create RSVP for accept action (as would be done when sending email)
        rsvp = RSVP.create_for_booking("BOOKING_ACCEPT", booking, user.user_email)

        response = api_client.get(f"/api/v1/rsvp/{rsvp.rsvp_code}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Booking accepted"
        assert response.data["action"] == "BOOKING_ACCEPT"

        booking.refresh_from_db()
        assert booking.status == "ACCEPTED"

    def test_reject_booking_via_link(self, api_client, user, user2, lend_thing):
        """Owner can reject booking via RSVP email link."""
        booking = BookingPeriod.objects.create(
            thing_code=lend_thing.thing_code,
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3),
        )

        # Create RSVP for reject action
        rsvp = RSVP.create_for_booking("BOOKING_REJECT", booking, user.user_email)

        response = api_client.get(f"/api/v1/rsvp/{rsvp.rsvp_code}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Booking rejected"
        assert response.data["action"] == "BOOKING_REJECT"

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

        # Create RSVP for accept action
        rsvp = RSVP.create_for_booking("BOOKING_ACCEPT", booking, user.user_email)

        response = api_client.get(f"/api/v1/rsvp/{rsvp.rsvp_code}/")

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

        # Create RSVP for accept action
        rsvp = RSVP.create_for_booking("BOOKING_ACCEPT", booking, user.user_email)

        response = api_client.get(f"/api/v1/rsvp/{rsvp.rsvp_code}/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_booking_not_found(self, api_client):
        """Should return 401 for non-existent RSVP."""
        response = api_client.get("/api/v1/rsvp/NOEXST/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestLendingThingStatusNotTaken:
    """Tests that LEND/RENT/SHARE things stay ACTIVE (not TAKEN)."""

    def test_lend_thing_stays_active_after_booking(self, user, user2, lend_thing, collection):
        """LEND_THING stays ACTIVE after booking request."""
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
        """RENT_THING stays ACTIVE after booking request."""
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
            thing_type=lend_thing.thing_type,
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3),
        )

        # Accept via RSVP
        rsvp = RSVP.create_for_booking("BOOKING_ACCEPT", booking, user.user_email)
        api_client.get(f"/api/v1/rsvp/{rsvp.rsvp_code}/")

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
    """Tests specific to RENT_THING with pricing."""

    def test_rent_thing_has_fee(self, rent_thing):
        """RENT_THING can have a fee."""
        assert rent_thing.thing_fee == 25.00

    def test_booking_rent_thing_works_same_as_lend(self, user, user2, rent_thing, collection):
        """Booking flow for RENT_THING is same as LEND_THING."""
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
    """Tests that GIFT/SELL/ORDER flow uses BookingPeriod without dates."""

    def test_gift_article_uses_standard_flow(self, user, user2, thing, collection):
        """GIFT_THING uses BookingPeriod without dates."""
        collection.add_invite(user2.user_code)

        client2 = get_client_for_user(user2)
        response = client2.post(f"/api/v1/things/{thing.thing_code}/request/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Booking request sent"
        assert "booking_code" in response.data
        # Should NOT have dates
        assert "start_date" not in response.data
        assert "end_date" not in response.data

        # Thing status should be TAKEN for GIFT_THING
        thing.refresh_from_db()
        assert thing.thing_status == "TAKEN"

    def test_sell_thing_uses_standard_flow(self, user, user2, collection):
        """SELL_THING uses BookingPeriod without dates, same as GIFT_THING."""
        from core.models import Thing

        sell_thing = Thing.objects.create(
            thing_code="SELL01",
            thing_type="SELL_THING",
            thing_owner=user.user_code,
            thing_headline="Item for Sale",
            thing_fee=50.00,
        )
        collection.add_thing(sell_thing.thing_code)
        collection.add_invite(user2.user_code)

        client2 = get_client_for_user(user2)
        response = client2.post(f"/api/v1/things/{sell_thing.thing_code}/request/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Booking request sent"
        assert "booking_code" in response.data

        # Thing status should be TAKEN for SELL_THING
        sell_thing.refresh_from_db()
        assert sell_thing.thing_status == "TAKEN"


@pytest.mark.django_db
class TestSingleUseThingCompleteFlow:
    """Tests for complete single-use thing reservation flow (GIFT/SELL)."""

    def test_complete_gift_flow_accept(self, api_client, user, user2, thing, collection):
        """Complete flow: create request → owner accepts → thing INACTIVE."""
        from core.models import RSVP
        from core.models.booking import BookingPeriod

        collection.add_invite(user2.user_code)

        # Step 1: Requester creates booking request
        client2 = get_client_for_user(user2)
        response = client2.post(f"/api/v1/things/{thing.thing_code}/request/")
        assert response.status_code == status.HTTP_200_OK
        booking_code = response.data["booking_code"]

        # Verify thing is TAKEN
        thing.refresh_from_db()
        assert thing.thing_status == "TAKEN"

        # Verify booking was created
        booking = BookingPeriod.objects.get(booking_code=booking_code)
        assert booking.status == "PENDING"
        assert booking.thing_type == "GIFT_THING"

        # Verify RSVPs were created for owner
        rsvps = RSVP.objects.filter(rsvp_target_code=booking_code)
        assert rsvps.count() == 2
        accept_rsvp = rsvps.get(rsvp_action="BOOKING_ACCEPT")
        assert accept_rsvp.user_email == user.user_email

        # Step 2: Owner accepts via RSVP
        response = api_client.get(f"/api/v1/rsvp/{accept_rsvp.rsvp_code}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["action"] == "BOOKING_ACCEPT"

        # Verify thing is now INACTIVE
        thing.refresh_from_db()
        assert thing.thing_status == "INACTIVE"
        assert thing.thing_available is False
        assert user2.user_code in thing.thing_deal

        # Verify booking is ACCEPTED
        booking.refresh_from_db()
        assert booking.status == "ACCEPTED"

        # Verify RSVP was deleted (one-time use)
        assert not RSVP.objects.filter(rsvp_code=accept_rsvp.rsvp_code).exists()

    def test_complete_gift_flow_reject(self, api_client, user, user2, thing, collection):
        """Complete flow: create request → owner rejects → thing ACTIVE again."""
        from core.models import RSVP
        from core.models.booking import BookingPeriod

        collection.add_invite(user2.user_code)

        # Step 1: Requester creates booking request
        client2 = get_client_for_user(user2)
        response = client2.post(f"/api/v1/things/{thing.thing_code}/request/")
        assert response.status_code == status.HTTP_200_OK
        booking_code = response.data["booking_code"]

        # Step 2: Owner rejects via RSVP
        reject_rsvp = RSVP.objects.get(rsvp_target_code=booking_code, rsvp_action="BOOKING_REJECT")
        response = api_client.get(f"/api/v1/rsvp/{reject_rsvp.rsvp_code}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["action"] == "BOOKING_REJECT"

        # Verify thing is back to ACTIVE
        thing.refresh_from_db()
        assert thing.thing_status == "ACTIVE"

        # Verify booking is REJECTED
        booking = BookingPeriod.objects.get(booking_code=booking_code)
        assert booking.status == "REJECTED"

    def test_cannot_request_taken_thing(self, user, user2, thing, collection):
        """Cannot request a thing that is already TAKEN."""
        collection.add_invite(user2.user_code)

        # First user makes a request
        client2 = get_client_for_user(user2)
        response = client2.post(f"/api/v1/things/{thing.thing_code}/request/")
        assert response.status_code == status.HTTP_200_OK

        # Create third user
        from core.models import User

        user3 = User.objects.create(
            user_code="TEST03",
            user_email="test3@example.com",
        )
        collection.add_invite(user3.user_code)

        # Third user tries to request same thing
        client3 = get_client_for_user(user3)
        response = client3.post(f"/api/v1/things/{thing.thing_code}/request/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Thing is not available for reservation"

    def test_thing_available_again_after_reject(self, api_client, user, user2, thing, collection):
        """After rejection, another user can request the thing."""
        from core.models import RSVP, User

        collection.add_invite(user2.user_code)

        # User2 makes request
        client2 = get_client_for_user(user2)
        response = client2.post(f"/api/v1/things/{thing.thing_code}/request/")
        booking_code = response.data["booking_code"]

        # Owner rejects
        reject_rsvp = RSVP.objects.get(rsvp_target_code=booking_code, rsvp_action="BOOKING_REJECT")
        api_client.get(f"/api/v1/rsvp/{reject_rsvp.rsvp_code}/")

        # Create user3
        user3 = User.objects.create(
            user_code="TEST03",
            user_email="test3@example.com",
        )
        collection.add_invite(user3.user_code)

        # User3 can now request
        client3 = get_client_for_user(user3)
        response = client3.post(f"/api/v1/things/{thing.thing_code}/request/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Booking request sent"


@pytest.mark.django_db
class TestOrderThingFlow:
    """Tests for ORDER_THING (repeatable orders with delivery_date and quantity)."""

    @pytest.fixture
    def order_thing(self, user, collection):
        """Create an ORDER_THING."""
        from core.models import Thing

        t = Thing.objects.create(
            thing_code="ORDER1",
            thing_type="ORDER_THING",
            thing_owner=user.user_code,
            thing_headline="Custom Cakes",
            thing_fee=25.00,
        )
        collection.add_thing(t.thing_code)
        return t

    def test_order_requires_delivery_date_and_quantity(self, user2, order_thing, collection):
        """ORDER_THING requires delivery_date and quantity in request."""
        collection.add_invite(user2.user_code)

        client2 = get_client_for_user(user2)

        # Request without data should fail
        response = client2.post(f"/api/v1/things/{order_thing.thing_code}/request/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Request with only delivery_date should fail
        response = client2.post(
            f"/api/v1/things/{order_thing.thing_code}/request/",
            {"delivery_date": str(date.today() + timedelta(days=7))},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Request with only quantity should fail
        response = client2.post(
            f"/api/v1/things/{order_thing.thing_code}/request/",
            {"quantity": 3},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_order_with_valid_data(self, user2, order_thing, collection):
        """ORDER_THING with valid delivery_date and quantity succeeds."""
        collection.add_invite(user2.user_code)

        client2 = get_client_for_user(user2)
        delivery_date = date.today() + timedelta(days=7)

        response = client2.post(
            f"/api/v1/things/{order_thing.thing_code}/request/",
            {"delivery_date": str(delivery_date), "quantity": 3},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Order request sent"
        assert "booking_code" in response.data
        assert response.data["delivery_date"] == str(delivery_date)
        assert response.data["quantity"] == 3

    def test_order_thing_stays_active(self, user2, order_thing, collection):
        """ORDER_THING stays ACTIVE after order request."""
        collection.add_invite(user2.user_code)

        client2 = get_client_for_user(user2)
        response = client2.post(
            f"/api/v1/things/{order_thing.thing_code}/request/",
            {"delivery_date": str(date.today() + timedelta(days=7)), "quantity": 2},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

        # Thing should still be ACTIVE
        order_thing.refresh_from_db()
        assert order_thing.thing_status == "ACTIVE"

    def test_multiple_orders_allowed(self, user, user2, order_thing, collection):
        """Multiple orders allowed for same ORDER_THING."""
        from core.models import User

        collection.add_invite(user2.user_code)

        # First order from user2
        client2 = get_client_for_user(user2)
        response1 = client2.post(
            f"/api/v1/things/{order_thing.thing_code}/request/",
            {"delivery_date": str(date.today() + timedelta(days=7)), "quantity": 2},
            format="json",
        )
        assert response1.status_code == status.HTTP_200_OK

        # Second order from different user
        user3 = User.objects.create(
            user_code="TEST03",
            user_email="test3@example.com",
        )
        collection.add_invite(user3.user_code)

        client3 = get_client_for_user(user3)
        response2 = client3.post(
            f"/api/v1/things/{order_thing.thing_code}/request/",
            {"delivery_date": str(date.today() + timedelta(days=14)), "quantity": 5},
            format="json",
        )
        assert response2.status_code == status.HTTP_200_OK

        # Both orders should exist
        assert response1.data["booking_code"] != response2.data["booking_code"]

    def test_same_user_can_order_multiple_times(self, user2, order_thing, collection):
        """Same user can make multiple orders for ORDER_THING."""
        collection.add_invite(user2.user_code)

        client2 = get_client_for_user(user2)

        # First order
        response1 = client2.post(
            f"/api/v1/things/{order_thing.thing_code}/request/",
            {"delivery_date": str(date.today() + timedelta(days=7)), "quantity": 2},
            format="json",
        )
        assert response1.status_code == status.HTTP_200_OK

        # Second order (different date)
        response2 = client2.post(
            f"/api/v1/things/{order_thing.thing_code}/request/",
            {"delivery_date": str(date.today() + timedelta(days=14)), "quantity": 3},
            format="json",
        )
        assert response2.status_code == status.HTTP_200_OK

    def test_order_accept_flow(self, api_client, user, user2, order_thing, collection):
        """Complete flow: order → accept → thing stays ACTIVE."""
        from core.models import RSVP
        from core.models.booking import BookingPeriod

        collection.add_invite(user2.user_code)

        # Step 1: Create order
        client2 = get_client_for_user(user2)
        delivery_date = date.today() + timedelta(days=7)
        response = client2.post(
            f"/api/v1/things/{order_thing.thing_code}/request/",
            {"delivery_date": str(delivery_date), "quantity": 3},
            format="json",
        )
        booking_code = response.data["booking_code"]

        # Verify booking has order info
        booking = BookingPeriod.objects.get(booking_code=booking_code)
        assert booking.delivery_date == delivery_date
        assert booking.quantity == 3
        assert booking.thing_type == "ORDER_THING"

        # Step 2: Accept via RSVP
        accept_rsvp = RSVP.objects.get(rsvp_target_code=booking_code, rsvp_action="BOOKING_ACCEPT")
        response = api_client.get(f"/api/v1/rsvp/{accept_rsvp.rsvp_code}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["action"] == "BOOKING_ACCEPT"
        assert response.data["delivery_date"] == str(delivery_date)
        assert response.data["quantity"] == 3

        # Verify thing is still ACTIVE
        order_thing.refresh_from_db()
        assert order_thing.thing_status == "ACTIVE"

        # Verify booking is ACCEPTED
        booking.refresh_from_db()
        assert booking.status == "ACCEPTED"

    def test_order_reject_flow(self, api_client, user, user2, order_thing, collection):
        """Complete flow: order → reject → thing stays ACTIVE."""
        from core.models import RSVP
        from core.models.booking import BookingPeriod

        collection.add_invite(user2.user_code)

        # Create order
        client2 = get_client_for_user(user2)
        response = client2.post(
            f"/api/v1/things/{order_thing.thing_code}/request/",
            {"delivery_date": str(date.today() + timedelta(days=7)), "quantity": 2},
            format="json",
        )
        booking_code = response.data["booking_code"]

        # Reject via RSVP
        reject_rsvp = RSVP.objects.get(rsvp_target_code=booking_code, rsvp_action="BOOKING_REJECT")
        response = api_client.get(f"/api/v1/rsvp/{reject_rsvp.rsvp_code}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["action"] == "BOOKING_REJECT"

        # Verify thing is still ACTIVE
        order_thing.refresh_from_db()
        assert order_thing.thing_status == "ACTIVE"

        # Verify booking is REJECTED
        booking = BookingPeriod.objects.get(booking_code=booking_code)
        assert booking.status == "REJECTED"

    def test_delivery_date_must_be_future(self, user2, order_thing, collection):
        """Delivery date must be today or in the future."""
        collection.add_invite(user2.user_code)

        client2 = get_client_for_user(user2)

        # Past date should fail
        response = client2.post(
            f"/api/v1/things/{order_thing.thing_code}/request/",
            {"delivery_date": str(date.today() - timedelta(days=1)), "quantity": 1},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_quantity_must_be_positive(self, user2, order_thing, collection):
        """Quantity must be at least 1."""
        collection.add_invite(user2.user_code)

        client2 = get_client_for_user(user2)

        # Zero quantity should fail
        response = client2.post(
            f"/api/v1/things/{order_thing.thing_code}/request/",
            {"delivery_date": str(date.today() + timedelta(days=7)), "quantity": 0},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Negative quantity should fail
        response = client2.post(
            f"/api/v1/things/{order_thing.thing_code}/request/",
            {"delivery_date": str(date.today() + timedelta(days=7)), "quantity": -1},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestDateBasedThingCompleteFlow:
    """Tests for complete date-based thing flow (LEND/RENT/SHARE)."""

    def test_complete_lend_flow_with_emails(self, api_client, user, user2, lend_thing, collection):
        """Complete flow: request with dates → owner email → accept → requester email."""
        from django.core import mail

        collection.add_invite(user2.user_code)

        # Step 1: Guest requests booking with dates
        client2 = get_client_for_user(user2)
        start = date.today() + timedelta(days=5)
        end = date.today() + timedelta(days=10)

        response = client2.post(
            f"/api/v1/things/{lend_thing.thing_code}/request/",
            {"start_date": str(start), "end_date": str(end)},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        booking_code = response.data["booking_code"]

        # Verify email sent to owner with dates
        assert len(mail.outbox) == 1
        owner_email = mail.outbox[0]
        assert user.user_email in owner_email.to
        assert str(start) in owner_email.body
        assert str(end) in owner_email.body

        # Step 2: Owner accepts via RSVP
        mail.outbox.clear()
        accept_rsvp = RSVP.objects.get(rsvp_target_code=booking_code, rsvp_action="BOOKING_ACCEPT")
        response = api_client.get(f"/api/v1/rsvp/{accept_rsvp.rsvp_code}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["start_date"] == str(start)
        assert response.data["end_date"] == str(end)

        # Verify confirmation email sent to requester with dates
        assert len(mail.outbox) == 1
        requester_email = mail.outbox[0]
        assert user2.user_email in requester_email.to
        assert "aceptada" in requester_email.body.lower()
        assert str(start) in requester_email.body

        # Verify thing stays ACTIVE
        lend_thing.refresh_from_db()
        assert lend_thing.thing_status == "ACTIVE"

    def test_complete_lend_flow_reject_with_emails(
        self, api_client, user, user2, lend_thing, collection
    ):
        """Complete flow: request → reject → requester notified → dates available."""
        from django.core import mail

        collection.add_invite(user2.user_code)

        # Step 1: Guest requests booking
        client2 = get_client_for_user(user2)
        start = date.today() + timedelta(days=5)
        end = date.today() + timedelta(days=10)

        response = client2.post(
            f"/api/v1/things/{lend_thing.thing_code}/request/",
            {"start_date": str(start), "end_date": str(end)},
            format="json",
        )
        booking_code = response.data["booking_code"]

        # Step 2: Owner rejects
        mail.outbox.clear()
        reject_rsvp = RSVP.objects.get(rsvp_target_code=booking_code, rsvp_action="BOOKING_REJECT")
        api_client.get(f"/api/v1/rsvp/{reject_rsvp.rsvp_code}/")

        # Verify rejection email sent to requester
        assert len(mail.outbox) == 1
        requester_email = mail.outbox[0]
        assert user2.user_email in requester_email.to
        assert "rechazada" in requester_email.body.lower()

        # Verify thing stays ACTIVE
        lend_thing.refresh_from_db()
        assert lend_thing.thing_status == "ACTIVE"

        # Step 3: Another user can now book those dates
        user3 = User.objects.create(user_code="TEST03", user_email="test3@example.com")
        collection.add_invite(user3.user_code)

        client3 = get_client_for_user(user3)
        response = client3.post(
            f"/api/v1/things/{lend_thing.thing_code}/request/",
            {"start_date": str(start), "end_date": str(end)},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_share_thing_stays_active_after_accept(self, api_client, user, user2, share_thing):
        """SHARE_THING stays ACTIVE after booking is accepted."""
        booking = BookingPeriod.objects.create(
            thing_code=share_thing.thing_code,
            thing_type="SHARE_THING",
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3),
        )

        # Accept via RSVP
        rsvp = RSVP.create_for_booking("BOOKING_ACCEPT", booking, user.user_email)
        api_client.get(f"/api/v1/rsvp/{rsvp.rsvp_code}/")

        share_thing.refresh_from_db()
        assert share_thing.thing_status == "ACTIVE"

    def test_calendar_shows_pending_and_accepted_only(
        self, authenticated_client, user, user2, lend_thing, collection
    ):
        """Calendar shows only PENDING and ACCEPTED, not REJECTED/EXPIRED."""
        collection.add_invite(user2.user_code)

        # Create bookings with different statuses
        BookingPeriod.objects.create(
            thing_code=lend_thing.thing_code,
            thing_type="LEND_THING",
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
            status="PENDING",
        )
        BookingPeriod.objects.create(
            thing_code=lend_thing.thing_code,
            thing_type="LEND_THING",
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=7),
            status="ACCEPTED",
        )
        BookingPeriod.objects.create(
            thing_code=lend_thing.thing_code,
            thing_type="LEND_THING",
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=12),
            status="REJECTED",
        )
        BookingPeriod.objects.create(
            thing_code=lend_thing.thing_code,
            thing_type="LEND_THING",
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
            start_date=date.today() + timedelta(days=15),
            end_date=date.today() + timedelta(days=17),
            status="EXPIRED",
        )

        # Get calendar
        response = authenticated_client.get(f"/api/v1/things/{lend_thing.thing_code}/calendar/")

        assert response.status_code == status.HTTP_200_OK
        # Should only show PENDING and ACCEPTED (2 bookings)
        assert len(response.data) == 2
        statuses = [b["status"] for b in response.data]
        assert "PENDING" in statuses
        assert "ACCEPTED" in statuses
        assert "REJECTED" not in statuses
        assert "EXPIRED" not in statuses

    def test_adjacent_bookings_allowed(self, user, user2, lend_thing, collection):
        """Bookings can be adjacent (one ends, next starts same day)."""
        collection.add_invite(user2.user_code)

        # Create first booking
        BookingPeriod.objects.create(
            thing_code=lend_thing.thing_code,
            thing_type="LEND_THING",
            requester_code=user2.user_code,
            requester_email=user2.user_email,
            owner_code=user.user_code,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            status="ACCEPTED",
        )

        # Create third user for second booking
        user3 = User.objects.create(user_code="TEST03", user_email="test3@example.com")
        collection.add_invite(user3.user_code)

        # Book starting the day after first ends
        client3 = get_client_for_user(user3)
        response = client3.post(
            f"/api/v1/things/{lend_thing.thing_code}/request/",
            {
                "start_date": str(date.today() + timedelta(days=6)),
                "end_date": str(date.today() + timedelta(days=10)),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
