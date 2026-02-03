"""
Collection views for OIUEEI.
"""

from django.conf import settings
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Collection, Theeeme, User
from core.serializers import (
    CollectionCreateSerializer,
    CollectionInviteSerializer,
    CollectionSerializer,
    CollectionUpdateSerializer,
)


class CollectionListView(APIView):
    """
    GET /api/v1/collections/
    List user's own collections.

    POST /api/v1/collections/
    Create a new collection.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        collections = Collection.objects.filter(collection_owner=request.user.user_code)
        serializer = CollectionSerializer(collections, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CollectionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Use default theeeme if not provided
        validated_data = serializer.validated_data
        if "collection_theeeme" not in validated_data:
            default_theeeme = Theeeme.objects.filter(theeeme_code="BRCLON").first()
            if default_theeeme:
                validated_data["collection_theeeme"] = default_theeeme

        collection = Collection.objects.create(
            collection_owner=request.user.user_code,
            **validated_data,
        )

        # Add to user's own collections
        if collection.collection_code not in request.user.user_own_collections:
            request.user.user_own_collections.append(collection.collection_code)
            request.user.save(update_fields=["user_own_collections"])

        return Response(
            CollectionSerializer(collection).data,
            status=status.HTTP_201_CREATED,
        )


class CollectionDetailView(APIView):
    """
    GET /api/v1/collections/{collection_code}/
    View a collection.

    PUT /api/v1/collections/{collection_code}/
    Update a collection (owner only).

    DELETE /api/v1/collections/{collection_code}/
    Delete a collection (owner only).
    """

    permission_classes = [IsAuthenticated]

    def get_collection(self, collection_code):
        try:
            return Collection.objects.get(collection_code=collection_code)
        except Collection.DoesNotExist:
            return None

    def get(self, request, collection_code):
        collection = self.get_collection(collection_code)
        if not collection:
            return Response(
                {"error": "Collection not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not collection.can_view(request.user.user_code):
            return Response(
                {"error": "Not authorized to view this collection"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CollectionSerializer(collection)
        return Response(serializer.data)

    def put(self, request, collection_code):
        collection = self.get_collection(collection_code)
        if not collection:
            return Response(
                {"error": "Collection not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not collection.is_owner(request.user.user_code):
            return Response(
                {"error": "Only the owner can update this collection"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CollectionUpdateSerializer(collection, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(CollectionSerializer(collection).data)

    def delete(self, request, collection_code):
        collection = self.get_collection(collection_code)
        if not collection:
            return Response(
                {"error": "Collection not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not collection.is_owner(request.user.user_code):
            return Response(
                {"error": "Only the owner can delete this collection"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Remove from user's collections
        if collection_code in request.user.user_own_collections:
            request.user.user_own_collections.remove(collection_code)
            request.user.save(update_fields=["user_own_collections"])

        collection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CollectionInviteView(APIView):
    """
    POST /api/v1/collections/{collection_code}/invite/
    Invite a user to a collection.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, collection_code):
        try:
            collection = Collection.objects.get(collection_code=collection_code)
        except Collection.DoesNotExist:
            return Response(
                {"error": "Collection not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not collection.is_owner(request.user.user_code):
            return Response(
                {"error": "Only the owner can invite users"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CollectionInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].lower()

        # Get or create user to invite
        invited_user, created = User.objects.get_or_create(
            user_email=email,
            defaults={"user_email": email},
        )

        # Add to collection invites
        collection.add_invite(invited_user.user_code)

        # Add to user's shared collections
        if collection_code not in invited_user.user_shared_collections:
            invited_user.user_shared_collections.append(collection_code)
            invited_user.save(update_fields=["user_shared_collections"])

        # Send invitation email
        magic_link_base = getattr(
            settings, "MAGIC_LINK_BASE_URL", "http://localhost:3000/magic-link"
        )

        send_mail(
            subject=f"{request.user.user_name or 'Someone'} te ha invitado a una colección",
            message=f"Has sido invitado a ver: {collection.collection_headline}",
            from_email=None,
            recipient_list=[email],
            html_message=f"""
            <html>
            <p>{request.user.user_name or 'Someone'} te ha invitado a ver:</p>
            <p><strong>{collection.collection_headline}</strong></p>
            <p>Accede para verlo: <a href="{magic_link_base}">{magic_link_base}</a></p>
            </html>
            """,
        )

        return Response(
            {
                "message": "Invitation sent",
                "email": email,
                "user_code": invited_user.user_code,
            },
            status=status.HTTP_200_OK,
        )


class SharedCollectionsView(APIView):
    """
    GET /api/v1/collections/shared/
    List collections shared with the current user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        shared_codes = request.user.user_shared_collections
        collections = Collection.objects.filter(collection_code__in=shared_codes)
        serializer = CollectionSerializer(collections, many=True)
        return Response(serializer.data)
