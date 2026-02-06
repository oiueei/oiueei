"""
Booking views for OIUEEI lending calendar.

All email action links use RSVP codes as intermediaries.
BookingAcceptView and BookingRejectView have been removed -
all accept/reject actions now go through the unified RSVP endpoint.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Thing
from core.models.booking import BookingPeriod
from core.serializers.booking import (
    BookingPeriodCalendarSerializer,
    BookingPeriodOwnerCalendarSerializer,
    BookingPeriodSerializer,
    MyBookingSerializer,
)


class ThingCalendarView(APIView):
    """
    GET /api/v1/things/{thing_code}/calendar/
    Get blocked periods for a thing's calendar.
    Owner sees full details, guests see only dates and status.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, thing_code):
        try:
            thing = Thing.objects.get(thing_code=thing_code)
        except Thing.DoesNotExist:
            return Response(
                {"error": "Thing not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if user can view this thing
        if not thing.can_view(request.user.user_code):
            return Response(
                {"error": "Not authorized to view this thing"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get blocked periods
        blocked_periods = BookingPeriod.get_blocked_periods(thing_code)

        # Owner sees full details, guests see limited info
        if thing.is_owner(request.user.user_code):
            serializer = BookingPeriodOwnerCalendarSerializer(blocked_periods, many=True)
        else:
            serializer = BookingPeriodCalendarSerializer(blocked_periods, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


# NOTE: BookingAcceptView and BookingRejectView have been removed.
# All booking accept/reject actions now go through the unified RSVP endpoint
# at /api/v1/rsvp/{rsvp_code}/ to avoid exposing real codes in URLs.


class MyBookingsView(APIView):
    """
    GET /api/v1/my-bookings/
    List all booking requests made by the current user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        bookings = BookingPeriod.objects.filter(requester_code=request.user.user_code).order_by(
            "-booking_created"
        )

        serializer = MyBookingSerializer(bookings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OwnerBookingsView(APIView):
    """
    GET /api/v1/owner-bookings/
    List all booking requests for things owned by the current user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get all things owned by user
        owned_things = Thing.objects.filter(thing_owner=request.user.user_code)
        thing_codes = [t.thing_code for t in owned_things]

        # Get all bookings for those things
        bookings = BookingPeriod.objects.filter(thing_code__in=thing_codes).order_by(
            "-booking_created"
        )

        serializer = BookingPeriodSerializer(bookings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
