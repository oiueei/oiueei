"""
User views for OIUEEI.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Collection, User
from core.serializers import UserPublicSerializer, UserSerializer, UserUpdateSerializer


def can_view_user(viewer_user_code, target_user_code):
    """
    Check if viewer can see target user's profile.
    Returns True if:
    - viewer is target (own profile)
    - target is in collection_invites of any collection owned by viewer
    - viewer is in collection_invites of any collection owned by target
    """
    if viewer_user_code == target_user_code:
        return True

    # Check if target is invited to any of viewer's collections
    # Using Python-side filtering for SQLite compatibility
    viewer_collections = Collection.objects.filter(collection_owner=viewer_user_code)
    for collection in viewer_collections:
        if target_user_code in collection.collection_invites:
            return True

    # Check if viewer is invited to any of target's collections
    target_collections = Collection.objects.filter(collection_owner=target_user_code)
    for collection in target_collections:
        if viewer_user_code in collection.collection_invites:
            return True

    return False


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

        # Check if viewer can see this user's profile
        if not can_view_user(request.user.user_code, user_code):
            return Response(
                {"error": "Not authorized to view this user's profile"},
                status=status.HTTP_403_FORBIDDEN,
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
