"""
Authentication views for OIUEEI.

Handles magic link authentication and RSVP-based actions.
RSVP serves as an intermediary for ALL email communications to avoid
exposing real codes (booking_code, thing_code, etc.) in URLs.
"""

import logging

from django.conf import settings
from django.contrib.auth import login
from django.core.mail import send_mail
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import RSVP, Collection, Thing, User
from core.models.booking import SINGLE_USE_TYPES, BookingPeriod
from core.serializers import RequestLinkSerializer, UserSerializer

security_logger = logging.getLogger("security")


class RequestLinkView(APIView):
    """
    POST /api/v1/auth/request-link/
    Request a magic link for authentication.
    """

    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key="ip", rate="5/m", method="POST", block=True))
    def post(self, request):
        serializer = RequestLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].lower()
        ip = self._get_client_ip(request)

        # INVITE-ONLY: Only existing users can request magic links
        try:
            user = User.objects.get(user_email=email)
        except User.DoesNotExist:
            security_logger.warning(
                f"Magic link request denied for non-existent user: {email} from IP {ip}"
            )
            return Response(
                {"error": "No account found. Please ask someone to invite you."},
                status=status.HTTP_404_NOT_FOUND,
            )

        security_logger.info(f"Magic link requested for {email} from IP {ip}")

        # Create RSVP
        rsvp = RSVP.objects.create(
            user_code=user.user_code,
            user_email=email,
        )

        # Send magic link email
        magic_link_base = getattr(
            settings, "MAGIC_LINK_BASE_URL", "http://localhost:3000/magic-link"
        )
        magic_link = f"{magic_link_base}/{rsvp.rsvp_code}"

        send_mail(
            subject="Tu enlace de acceso a OIUEEI",
            message=f"Hola! Haz clic aquí para acceder: {magic_link}",
            from_email=None,
            recipient_list=[email],
            html_message=f"""
            <html>
            <p>Hola! Haz clic aquí para acceder:</p>
            <a href="{magic_link}">Acceder</a>
            </html>
            """,
        )

        return Response(
            {"message": "Magic link sent", "email": email},
            status=status.HTTP_200_OK,
        )

    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")


class VerifyLinkView(APIView):
    """
    GET /api/v1/auth/verify/{rsvp_code}/
    Process an RSVP action.

    Handles all RSVP-based actions:
    - MAGIC_LINK: Verify magic link and return JWT token
    - COLLECTION_INVITE: Accept collection invitation and return JWT token
    - BOOKING_ACCEPT: Accept a booking (all thing types)
    - BOOKING_REJECT: Reject a booking (all thing types)
    """

    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key="ip", rate="10/m", method="GET", block=True))
    def get(self, request, rsvp_code):
        ip = self._get_client_ip(request)

        try:
            rsvp = RSVP.objects.get(rsvp_code=rsvp_code)
        except RSVP.DoesNotExist:
            security_logger.warning(f"Invalid RSVP code attempted from IP {ip}")
            return Response(
                {"error": "Invalid or expired link"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not rsvp.is_valid():
            security_logger.warning(f"Expired RSVP code used from IP {ip}")
            rsvp.delete()
            return Response(
                {"error": "Link expired"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Route to appropriate handler based on action type
        action_handlers = {
            "MAGIC_LINK": self._handle_magic_link,
            "COLLECTION_INVITE": self._handle_collection_invite,
            "BOOKING_ACCEPT": self._handle_booking_accept,
            "BOOKING_REJECT": self._handle_booking_reject,
        }

        handler = action_handlers.get(rsvp.rsvp_action, self._handle_magic_link)
        return handler(request, rsvp)

    def _handle_magic_link(self, request, rsvp):
        """Handle magic link authentication."""
        ip = self._get_client_ip(request)

        # Get user
        try:
            user = User.objects.get(user_code=rsvp.user_code)
        except User.DoesNotExist:
            rsvp.delete()
            return Response(
                {"error": "User not found"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Update last activity
        user.update_last_activity()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # Also login via session for browser access
        login(request, user)

        # Delete RSVP (one-time use)
        rsvp.delete()

        security_logger.info(f"User {user.user_email} logged in via magic link from IP {ip}")

        # Return token and user data
        user_data = UserSerializer(user).data

        return Response(
            {
                "action": "MAGIC_LINK",
                "token": str(refresh.access_token),
                "refresh": str(refresh),
                "user": user_data,
            },
            status=status.HTTP_200_OK,
        )

    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")

    def _handle_collection_invite(self, request, rsvp):
        """Handle collection invitation acceptance."""
        # Get user
        try:
            user = User.objects.get(user_code=rsvp.user_code)
        except User.DoesNotExist:
            rsvp.delete()
            return Response(
                {"error": "User not found"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Update last activity
        user.update_last_activity()

        # Process collection invitation
        invited_collection = None
        if rsvp.collection_code:
            try:
                collection = Collection.objects.get(collection_code=rsvp.collection_code)
                # Add user to collection invites
                collection.add_invite(user.user_code)
                # Add collection to user's shared collections
                if rsvp.collection_code not in user.user_invited_collections:
                    user.user_invited_collections.append(rsvp.collection_code)
                    user.save(update_fields=["user_invited_collections"])
                invited_collection = rsvp.collection_code
            except Collection.DoesNotExist:
                pass  # Collection was deleted, ignore

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # Also login via session for browser access
        login(request, user)

        # Delete RSVP (one-time use)
        rsvp.delete()

        # Return token and user data
        user_data = UserSerializer(user).data

        response_data = {
            "action": "COLLECTION_INVITE",
            "token": str(refresh.access_token),
            "refresh": str(refresh),
            "user": user_data,
        }

        if invited_collection:
            response_data["invited_collection"] = invited_collection

        return Response(response_data, status=status.HTTP_200_OK)

    def _handle_booking_accept(self, request, rsvp):
        """Handle booking accept action for all thing types."""
        booking_code = rsvp.rsvp_target_code

        try:
            booking = BookingPeriod.objects.get(booking_code=booking_code)
        except BookingPeriod.DoesNotExist:
            rsvp.delete()
            return Response(
                {"error": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not booking.is_valid():
            rsvp.delete()
            return Response(
                {"error": "Booking expired or already processed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get thing
        try:
            thing = Thing.objects.get(thing_code=booking.thing_code)
        except Thing.DoesNotExist:
            rsvp.delete()
            return Response(
                {"error": "Thing not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Accept the booking
        booking.accept()

        # For GIFT/SELL: Mark thing as INACTIVE and add requester to deal
        if booking.thing_type in SINGLE_USE_TYPES:
            thing.thing_status = "INACTIVE"
            thing.thing_available = False
            if booking.requester_code not in thing.thing_deal:
                thing.thing_deal.append(booking.requester_code)
            thing.save(update_fields=["thing_status", "thing_available", "thing_deal"])

        # Build email content based on booking type
        if booking.start_date and booking.end_date:
            # Date-based booking (LEND/RENT/SHARE)
            message = (
                f"Tu solicitud de reserva para '{thing.thing_headline}' "
                f"del {booking.start_date} al {booking.end_date} ha sido aceptada."
            )
            html_extra = f"<p>Fechas: {booking.start_date} - {booking.end_date}</p>"
            subject = f"Tu reserva ha sido aceptada: {thing.thing_headline}"
        elif booking.delivery_date:
            # Order (ORDER_THING)
            message = (
                f"Tu pedido de {booking.quantity}x '{thing.thing_headline}' "
                f"para el {booking.delivery_date} ha sido aceptado."
            )
            html_extra = (
                f"<p>Cantidad: {booking.quantity}</p>"
                f"<p>Fecha de entrega: {booking.delivery_date}</p>"
            )
            subject = f"Tu pedido ha sido aceptado: {thing.thing_headline}"
        else:
            # Simple booking (GIFT/SELL)
            message = f"Tu solicitud de reserva para '{thing.thing_headline}' ha sido aceptada."
            html_extra = ""
            subject = f"Tu reserva ha sido aceptada: {thing.thing_headline}"

        # Send confirmation email to requester
        send_mail(
            subject=subject,
            message=message,
            from_email=None,
            recipient_list=[booking.requester_email],
            html_message=f"""
            <html>
            <p>Tu solicitud ha sido <strong>aceptada</strong>:</p>
            <p><strong>{thing.thing_headline}</strong></p>
            {html_extra}
            </html>
            """,
        )

        # Delete RSVP (one-time use)
        rsvp.delete()

        # Build response
        response_data = {
            "action": "BOOKING_ACCEPT",
            "message": "Booking accepted",
            "thing_headline": thing.thing_headline,
        }
        if booking.start_date:
            response_data["start_date"] = str(booking.start_date)
        if booking.end_date:
            response_data["end_date"] = str(booking.end_date)
        if booking.delivery_date:
            response_data["delivery_date"] = str(booking.delivery_date)
        if booking.quantity:
            response_data["quantity"] = booking.quantity

        return Response(response_data, status=status.HTTP_200_OK)

    def _handle_booking_reject(self, request, rsvp):
        """Handle booking reject action for all thing types."""
        booking_code = rsvp.rsvp_target_code

        try:
            booking = BookingPeriod.objects.get(booking_code=booking_code)
        except BookingPeriod.DoesNotExist:
            rsvp.delete()
            return Response(
                {"error": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not booking.is_valid():
            rsvp.delete()
            return Response(
                {"error": "Booking expired or already processed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get thing
        try:
            thing = Thing.objects.get(thing_code=booking.thing_code)
        except Thing.DoesNotExist:
            rsvp.delete()
            return Response(
                {"error": "Thing not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Reject the booking
        booking.reject()

        # For GIFT/SELL: Restore thing to ACTIVE (was set to TAKEN when request was made)
        if booking.thing_type in SINGLE_USE_TYPES:
            thing.thing_status = "ACTIVE"
            thing.save(update_fields=["thing_status"])

        # Build email content based on booking type
        if booking.start_date and booking.end_date:
            # Date-based booking (LEND/RENT/SHARE)
            message = (
                f"Tu solicitud de reserva para '{thing.thing_headline}' "
                f"del {booking.start_date} al {booking.end_date} ha sido rechazada."
            )
            html_extra = f"<p>Fechas: {booking.start_date} - {booking.end_date}</p>"
            subject = f"Tu reserva ha sido rechazada: {thing.thing_headline}"
        elif booking.delivery_date:
            # Order (ORDER_THING)
            message = (
                f"Tu pedido de {booking.quantity}x '{thing.thing_headline}' "
                f"para el {booking.delivery_date} ha sido rechazado."
            )
            html_extra = (
                f"<p>Cantidad: {booking.quantity}</p>"
                f"<p>Fecha de entrega: {booking.delivery_date}</p>"
            )
            subject = f"Tu pedido ha sido rechazado: {thing.thing_headline}"
        else:
            # Simple booking (GIFT/SELL)
            message = f"Tu solicitud de reserva para '{thing.thing_headline}' ha sido rechazada."
            html_extra = ""
            subject = f"Tu reserva ha sido rechazada: {thing.thing_headline}"

        # Send rejection email to requester
        send_mail(
            subject=subject,
            message=message,
            from_email=None,
            recipient_list=[booking.requester_email],
            html_message=f"""
            <html>
            <p>Tu solicitud ha sido <strong>rechazada</strong>:</p>
            <p><strong>{thing.thing_headline}</strong></p>
            {html_extra}
            </html>
            """,
        )

        # Delete RSVP (one-time use)
        rsvp.delete()

        return Response(
            {
                "action": "BOOKING_REJECT",
                "message": "Booking rejected",
                "thing_headline": thing.thing_headline,
            },
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    """
    GET /api/v1/auth/me/
    Get current authenticated user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user.update_last_activity()
        serializer = UserSerializer(user)
        return Response(serializer.data)


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/
    Logout the current user.

    Optionally accepts a refresh token to blacklist it.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.contrib.auth import logout

        # Try to blacklist the refresh token if provided
        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                # Blacklist might not be enabled or token invalid
                pass

        # Logout from Django session
        logout(request)

        return Response(
            {"message": "Successfully logged out"},
            status=status.HTTP_200_OK,
        )
