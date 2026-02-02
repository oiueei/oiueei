"""
FAQ views for OIUEEI.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import FAQ, Thing
from core.serializers import FAQAnswerSerializer, FAQCreateSerializer, FAQSerializer


class ThingFAQListView(APIView):
    """
    GET /api/v1/things/{thing_code}/faq/
    List FAQs for a thing.

    POST /api/v1/things/{thing_code}/faq/
    Ask a question about a thing.
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

        # Get visible FAQs (or all if owner)
        if thing.is_owner(request.user.user_code):
            faqs = FAQ.objects.filter(faq_thing=thing_code)
        else:
            faqs = FAQ.objects.filter(faq_thing=thing_code, faq_is_visible=True)

        serializer = FAQSerializer(faqs, many=True)
        return Response(serializer.data)

    def post(self, request, thing_code):
        thing = self.get_thing(thing_code)
        if not thing:
            return Response(
                {"error": "Thing not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = FAQCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        faq = FAQ.objects.create(
            faq_thing=thing_code,
            faq_questioner=request.user.user_code,
            faq_question=serializer.validated_data["faq_question"],
        )

        # Add FAQ to thing
        thing.add_faq(faq.faq_code)

        return Response(
            FAQSerializer(faq).data,
            status=status.HTTP_201_CREATED,
        )


class FAQDetailView(APIView):
    """
    GET /api/v1/faq/{faq_code}/
    View a FAQ.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, faq_code):
        try:
            faq = FAQ.objects.get(faq_code=faq_code)
        except FAQ.DoesNotExist:
            return Response(
                {"error": "FAQ not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check visibility
        if not faq.faq_is_visible:
            # Only owner of thing or questioner can see hidden FAQs
            try:
                thing = Thing.objects.get(thing_code=faq.faq_thing)
                if (
                    not thing.is_owner(request.user.user_code)
                    and faq.faq_questioner != request.user.user_code
                ):
                    return Response(
                        {"error": "FAQ not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            except Thing.DoesNotExist:
                pass

        serializer = FAQSerializer(faq)
        return Response(serializer.data)


class FAQAnswerView(APIView):
    """
    POST /api/v1/faq/{faq_code}/answer/
    Answer a FAQ (thing owner only).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, faq_code):
        try:
            faq = FAQ.objects.get(faq_code=faq_code)
        except FAQ.DoesNotExist:
            return Response(
                {"error": "FAQ not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if user is thing owner
        try:
            thing = Thing.objects.get(thing_code=faq.faq_thing)
        except Thing.DoesNotExist:
            return Response(
                {"error": "Thing not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not thing.is_owner(request.user.user_code):
            return Response(
                {"error": "Only the thing owner can answer questions"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = FAQAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        faq.answer(serializer.validated_data["faq_answer"])

        return Response(FAQSerializer(faq).data)
