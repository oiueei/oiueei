"""
Reservation views for OIUEEI.
"""

from django.conf import settings
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import ReservationRequest, Thing, User


class ThingRequestView(APIView):
    """
    POST /api/v1/things/{thing_code}/request/
    Request a reservation for a thing.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, thing_code):
        try:
            thing = Thing.objects.get(thing_code=thing_code)
        except Thing.DoesNotExist:
            return Response(
                {"error": "Thing not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if user can view this thing (is invited to collection)
        if not thing.can_view(request.user.user_code):
            return Response(
                {"error": "Not authorized to request this thing"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Owner cannot request their own thing
        if thing.is_owner(request.user.user_code):
            return Response(
                {"error": "Cannot request your own thing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if thing is available
        if thing.thing_status != "ACTIVE":
            return Response(
                {"error": "Thing is not available for reservation"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if user already has a pending request for this thing
        existing = ReservationRequest.objects.filter(
            thing_code=thing_code,
            requester_code=request.user.user_code,
            status="PENDING",
        ).first()
        if existing:
            return Response(
                {"error": "You already have a pending request for this thing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create reservation request
        reservation = ReservationRequest.objects.create(
            thing_code=thing_code,
            requester_code=request.user.user_code,
            requester_email=request.user.user_email,
            owner_code=thing.thing_owner,
        )

        # Update thing status to TAKEN
        thing.thing_status = "TAKEN"
        thing.save(update_fields=["thing_status"])

        # Get owner info
        try:
            owner = User.objects.get(user_code=thing.thing_owner)
            owner_email = owner.user_email
        except User.DoesNotExist:
            return Response(
                {"error": "Thing owner not found"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Send email to owner with accept/reject links
        base_url = getattr(settings, "RESERVATION_BASE_URL", "http://localhost:3000/reservations")
        accept_link = f"{base_url}/{reservation.reservation_code}/accept"
        reject_link = f"{base_url}/{reservation.reservation_code}/reject"

        requester_name = request.user.user_name or request.user.user_email

        send_mail(
            subject=f"{requester_name} quiere reservar: {thing.thing_headline}",
            message=f"{requester_name} ha solicitado reservar '{thing.thing_headline}'. "
            f"Aceptar: {accept_link} | Rechazar: {reject_link}",
            from_email=None,
            recipient_list=[owner_email],
            html_message=f"""
            <html>
            <p><strong>{requester_name}</strong> ha solicitado reservar:</p>
            <p><strong>{thing.thing_headline}</strong></p>
            <p>
                <a href="{accept_link}">Aceptar reserva</a> |
                <a href="{reject_link}">Rechazar reserva</a>
            </p>
            </html>
            """,
        )

        return Response(
            {
                "message": "Reservation request sent",
                "reservation_code": reservation.reservation_code,
            },
            status=status.HTTP_200_OK,
        )


class ReservationAcceptView(APIView):
    """
    GET /api/v1/reservations/{reservation_code}/accept/
    Accept a reservation request (via email link).
    """

    permission_classes = [AllowAny]

    def get(self, request, reservation_code):
        try:
            reservation = ReservationRequest.objects.get(reservation_code=reservation_code)
        except ReservationRequest.DoesNotExist:
            return Response(
                {"error": "Reservation not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not reservation.is_valid():
            return Response(
                {"error": "Reservation expired or already processed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get thing
        try:
            thing = Thing.objects.get(thing_code=reservation.thing_code)
        except Thing.DoesNotExist:
            return Response(
                {"error": "Thing not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Accept the reservation
        reservation.accept()

        # Update thing status to INACTIVE and add requester to deal
        thing.thing_status = "INACTIVE"
        thing.thing_available = False
        if reservation.requester_code not in thing.thing_deal:
            thing.thing_deal.append(reservation.requester_code)
        thing.save(update_fields=["thing_status", "thing_available", "thing_deal"])

        # Send confirmation email to requester
        send_mail(
            subject=f"Tu reserva ha sido aceptada: {thing.thing_headline}",
            message=f"Tu solicitud de reserva para '{thing.thing_headline}' " "ha sido aceptada.",
            from_email=None,
            recipient_list=[reservation.requester_email],
            html_message=f"""
            <html>
            <p>Tu solicitud de reserva ha sido <strong>aceptada</strong>:</p>
            <p><strong>{thing.thing_headline}</strong></p>
            </html>
            """,
        )

        return Response(
            {
                "message": "Reservation accepted",
                "thing_code": thing.thing_code,
                "requester_code": reservation.requester_code,
            },
            status=status.HTTP_200_OK,
        )


class ReservationRejectView(APIView):
    """
    GET /api/v1/reservations/{reservation_code}/reject/
    Reject a reservation request (via email link).
    """

    permission_classes = [AllowAny]

    def get(self, request, reservation_code):
        try:
            reservation = ReservationRequest.objects.get(reservation_code=reservation_code)
        except ReservationRequest.DoesNotExist:
            return Response(
                {"error": "Reservation not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not reservation.is_valid():
            return Response(
                {"error": "Reservation expired or already processed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get thing
        try:
            thing = Thing.objects.get(thing_code=reservation.thing_code)
        except Thing.DoesNotExist:
            return Response(
                {"error": "Thing not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Reject the reservation
        reservation.reject()

        # Update thing status back to ACTIVE
        thing.thing_status = "ACTIVE"
        thing.save(update_fields=["thing_status"])

        # Send rejection email to requester
        send_mail(
            subject=f"Tu reserva ha sido rechazada: {thing.thing_headline}",
            message=f"Tu solicitud de reserva para '{thing.thing_headline}' " "ha sido rechazada.",
            from_email=None,
            recipient_list=[reservation.requester_email],
            html_message=f"""
            <html>
            <p>Tu solicitud de reserva ha sido <strong>rechazada</strong>:</p>
            <p><strong>{thing.thing_headline}</strong></p>
            </html>
            """,
        )

        return Response(
            {
                "message": "Reservation rejected",
                "thing_code": thing.thing_code,
                "requester_code": reservation.requester_code,
            },
            status=status.HTTP_200_OK,
        )
