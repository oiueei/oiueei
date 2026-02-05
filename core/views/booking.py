"""
Booking views for OIUEEI lending calendar.
"""

from django.core.mail import send_mail
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
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


class BookingAcceptView(APIView):
    """
    GET /api/v1/bookings/{booking_code}/accept/
    Accept a booking request (via email link).
    """

    permission_classes = [AllowAny]

    def get(self, request, booking_code):
        try:
            booking = BookingPeriod.objects.get(booking_code=booking_code)
        except BookingPeriod.DoesNotExist:
            return Response(
                {"error": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not booking.is_valid():
            return Response(
                {"error": "Booking expired or already processed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get thing
        try:
            thing = Thing.objects.get(thing_code=booking.thing_code)
        except Thing.DoesNotExist:
            return Response(
                {"error": "Thing not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Accept the booking
        booking.accept()

        # Send confirmation email to requester
        send_mail(
            subject=f"Tu reserva ha sido aceptada: {thing.thing_headline}",
            message=f"Tu solicitud de reserva para '{thing.thing_headline}' "
            f"del {booking.start_date} al {booking.end_date} ha sido aceptada.",
            from_email=None,
            recipient_list=[booking.requester_email],
            html_message=f"""
            <html>
            <p>Tu solicitud de reserva ha sido <strong>aceptada</strong>:</p>
            <p><strong>{thing.thing_headline}</strong></p>
            <p>Fechas: {booking.start_date} - {booking.end_date}</p>
            </html>
            """,
        )

        return Response(
            {
                "message": "Booking accepted",
                "booking_code": booking.booking_code,
                "thing_code": thing.thing_code,
                "start_date": str(booking.start_date),
                "end_date": str(booking.end_date),
            },
            status=status.HTTP_200_OK,
        )


class BookingRejectView(APIView):
    """
    GET /api/v1/bookings/{booking_code}/reject/
    Reject a booking request (via email link).
    """

    permission_classes = [AllowAny]

    def get(self, request, booking_code):
        try:
            booking = BookingPeriod.objects.get(booking_code=booking_code)
        except BookingPeriod.DoesNotExist:
            return Response(
                {"error": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not booking.is_valid():
            return Response(
                {"error": "Booking expired or already processed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get thing
        try:
            thing = Thing.objects.get(thing_code=booking.thing_code)
        except Thing.DoesNotExist:
            return Response(
                {"error": "Thing not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Reject the booking
        booking.reject()

        # Send rejection email to requester
        send_mail(
            subject=f"Tu reserva ha sido rechazada: {thing.thing_headline}",
            message=f"Tu solicitud de reserva para '{thing.thing_headline}' "
            f"del {booking.start_date} al {booking.end_date} ha sido rechazada.",
            from_email=None,
            recipient_list=[booking.requester_email],
            html_message=f"""
            <html>
            <p>Tu solicitud de reserva ha sido <strong>rechazada</strong>:</p>
            <p><strong>{thing.thing_headline}</strong></p>
            <p>Fechas: {booking.start_date} - {booking.end_date}</p>
            </html>
            """,
        )

        return Response(
            {
                "message": "Booking rejected",
                "booking_code": booking.booking_code,
                "thing_code": thing.thing_code,
            },
            status=status.HTTP_200_OK,
        )


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
