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

    def get(self, request, thing_code):
        thing = self.get_thing(thing_code)
        if not thing:
            return Response(
                {"error": "Thing not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not thing.can_view(request.user.user_code):
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
            if thing_code in collection.collection_things:
                collection.remove_thing(thing_code)

        thing.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# NOTE: ThingReserveView and ThingReleaseView have been removed.
# All reservations now go through ThingRequestView which uses the BookingPeriod flow
# with owner approval via RSVP links.


class InvitedThingsView(APIView):
    """
    GET /api/v1/invited-things/
    List things from collections where the current user is invited.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_code = request.user.user_code

        # Get all collections where user is invited (Python-side filtering for SQLite)
        all_collections = Collection.objects.all()
        invited_collections = [c for c in all_collections if user_code in c.collection_invites]

        # Collect all thing codes from those collections
        thing_codes = []
        for collection in invited_collections:
            thing_codes.extend(collection.collection_things)

        # Remove duplicates
        thing_codes = list(set(thing_codes))

        # Get things that are available (thing_available=True)
        # Hidden things (thing_available=False) are only visible to owner
        things = Thing.objects.filter(thing_code__in=thing_codes, thing_available=True)
        serializer = ThingSerializer(things, many=True)
        return Response(serializer.data)
