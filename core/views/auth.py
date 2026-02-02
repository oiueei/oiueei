"""
Authentication views for OIUEEI.
"""

from django.conf import settings
from django.contrib.auth import login
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import RSVP, User
from core.serializers import RequestLinkSerializer, UserSerializer


class RequestLinkView(APIView):
    """
    POST /api/v1/auth/request-link/
    Request a magic link for authentication.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RequestLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].lower()

        # Get or create user
        user, created = User.objects.get_or_create(
            user_email=email,
            defaults={"user_email": email},
        )

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


class VerifyLinkView(APIView):
    """
    GET /api/v1/auth/verify/{rsvp_code}/
    Verify a magic link and return JWT token.
    """

    permission_classes = [AllowAny]

    def get(self, request, rsvp_code):
        try:
            rsvp = RSVP.objects.get(rsvp_code=rsvp_code)
        except RSVP.DoesNotExist:
            return Response(
                {"error": "Invalid or expired link"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not rsvp.is_valid():
            rsvp.delete()
            return Response(
                {"error": "Link expired"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

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

        # Return token and user data
        user_data = UserSerializer(user).data

        return Response(
            {
                "token": str(refresh.access_token),
                "refresh": str(refresh),
                "user": user_data,
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
