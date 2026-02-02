"""
Thing views for OIUEEI.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Collection, Thing
from core.serializers import ThingCreateSerializer, ThingSerializer, ThingUpdateSerializer


class ThingListView(APIView):
    """
    GET /api/v1/things/
    List user's own things.

    POST /api/v1/things/
    Create a new thing.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        things = Thing.objects.filter(thing_owner=request.user.user_code)
        serializer = ThingSerializer(things, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ThingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        thing = Thing.objects.create(
            thing_owner=request.user.user_code,
            **serializer.validated_data,
        )

        # Add to user's things
        if thing.thing_code not in request.user.user_things:
            request.user.user_things.append(thing.thing_code)
            request.user.save(update_fields=["user_things"])

        # If collection_code is provided, add to collection
        collection_code = request.data.get("collection_code")
        if collection_code:
            try:
                collection = Collection.objects.get(collection_code=collection_code)
                if collection.is_owner(request.user.user_code):
                    collection.add_thing(thing.thing_code)
            except Collection.DoesNotExist:
                pass

        return Response(
            ThingSerializer(thing).data,
            status=status.HTTP_201_CREATED,
        )


class ThingDetailView(APIView):
    """
    GET /api/v1/things/{thing_code}/
    View a thing.

    PUT /api/v1/things/{thing_code}/
    Update a thing (owner only).

    DELETE /api/v1/things/{thing_code}/
    Delete a thing (owner only).
    """

    permission_classes = [IsAuthenticated]

    def get_thing(self, thing_code):
        try:
            return Thing.objects.get(thing_code=thing_code)
        except Thing.DoesNotExist:
            return None

    def can_view_thing(self, user, thing):
        """Check if user can view this thing (owner or in a shared collection)."""
        if thing.is_owner(user.user_code):
            return True

        # Check if thing is in any collection shared with user
        for collection_code in user.user_shared_collections:
            try:
                collection = Collection.objects.get(collection_code=collection_code)
                if thing.thing_code in collection.collection_articles:
                    return True
            except Collection.DoesNotExist:
                pass

        return False

    def get(self, request, thing_code):
        thing = self.get_thing(thing_code)
        if not thing:
            return Response(
                {"error": "Thing not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not self.can_view_thing(request.user, thing):
            return Response(
                {"error": "Not authorized to view this thing"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ThingSerializer(thing)
        return Response(serializer.data)

    def put(self, request, thing_code):
        thing = self.get_thing(thing_code)
        if not thing:
            return Response(
                {"error": "Thing not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not thing.is_owner(request.user.user_code):
            return Response(
                {"error": "Only the owner can update this thing"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ThingUpdateSerializer(thing, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(ThingSerializer(thing).data)

    def delete(self, request, thing_code):
        thing = self.get_thing(thing_code)
        if not thing:
            return Response(
                {"error": "Thing not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not thing.is_owner(request.user.user_code):
            return Response(
                {"error": "Only the owner can delete this thing"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Remove from user's things
        if thing_code in request.user.user_things:
            request.user.user_things.remove(thing_code)
            request.user.save(update_fields=["user_things"])

        # Remove from all collections
        for collection in Collection.objects.filter(collection_owner=request.user.user_code):
            if thing_code in collection.collection_articles:
                collection.remove_thing(thing_code)

        thing.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ThingReserveView(APIView):
    """
    POST /api/v1/things/{thing_code}/reserve/
    Reserve a thing.
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

        if thing.is_owner(request.user.user_code):
            return Response(
                {"error": "Cannot reserve your own thing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not thing.thing_available:
            return Response(
                {"error": "Thing is not available"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        thing.reserve(request.user.user_code)

        return Response(
            {
                "message": "Thing reserved",
                "thing": ThingSerializer(thing).data,
            },
            status=status.HTTP_200_OK,
        )


class ThingReleaseView(APIView):
    """
    POST /api/v1/things/{thing_code}/release/
    Release a reservation.
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

        if request.user.user_code not in thing.thing_deal:
            return Response(
                {"error": "You have not reserved this thing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        thing.release(request.user.user_code)

        return Response(
            {
                "message": "Reservation released",
                "thing": ThingSerializer(thing).data,
            },
            status=status.HTTP_200_OK,
        )
