"""
User views for OIUEEI.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import User
from core.serializers import UserPublicSerializer, UserSerializer, UserUpdateSerializer


class UserDetailView(APIView):
    """
    GET /api/v1/users/{user_code}/
    Get a user's public profile.

    PUT /api/v1/users/{user_code}/
    Update own profile (authenticated user only).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, user_code):
        try:
            user = User.objects.get(user_code=user_code)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # If viewing own profile, return full data
        if request.user.user_code == user_code:
            serializer = UserSerializer(user)
        else:
            serializer = UserPublicSerializer(user)

        return Response(serializer.data)

    def put(self, request, user_code):
        # Can only update own profile
        if request.user.user_code != user_code:
            return Response(
                {"error": "Cannot update another user's profile"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(UserSerializer(request.user).data)
