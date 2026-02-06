"""
URL configuration for core app.

IMPORTANT: All email action links use RSVP codes as intermediaries.
Never expose real codes (booking_code, reservation_code, etc.) in URLs.
"""

from django.urls import path

from .views.auth import LogoutView, MeView, RequestLinkView, VerifyLinkView
from .views.booking import MyBookingsView, OwnerBookingsView, ThingCalendarView
from .views.collections import (
    CollectionDetailView,
    CollectionInviteView,
    CollectionListView,
    InvitedCollectionsView,
)
from .views.faq import FAQAnswerView, FAQDetailView, FAQVisibilityView, ThingFAQListView
from .views.reservations import ThingRequestView
from .views.things import (
    InvitedThingsView,
    ThingDetailView,
    ThingListView,
    ThingReleaseView,
    ThingReserveView,
)
from .views.users import UserDetailView

urlpatterns = [
    # Auth & RSVP Actions
    path("auth/request-link/", RequestLinkView.as_view(), name="request-link"),
    path("auth/verify/<str:rsvp_code>/", VerifyLinkView.as_view(), name="verify-link"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    # RSVP action endpoint (unified handler for all email-based actions)
    # Handles: MAGIC_LINK, COLLECTION_INVITE, RESERVATION_ACCEPT/REJECT, BOOKING_ACCEPT/REJECT
    path("rsvp/<str:rsvp_code>/", VerifyLinkView.as_view(), name="rsvp-action"),
    # Users
    path("users/<str:user_code>/", UserDetailView.as_view(), name="user-detail"),
    # Collections
    path("collections/", CollectionListView.as_view(), name="collection-list"),
    path(
        "invited-collections/",
        InvitedCollectionsView.as_view(),
        name="invited-collections",
    ),
    path(
        "collections/<str:collection_code>/",
        CollectionDetailView.as_view(),
        name="collection-detail",
    ),
    path(
        "collections/<str:collection_code>/invite/",
        CollectionInviteView.as_view(),
        name="collection-invite",
    ),
    # Things
    path("things/", ThingListView.as_view(), name="thing-list"),
    path("invited-things/", InvitedThingsView.as_view(), name="invited-things"),
    path("things/<str:thing_code>/", ThingDetailView.as_view(), name="thing-detail"),
    path("things/<str:thing_code>/reserve/", ThingReserveView.as_view(), name="thing-reserve"),
    path("things/<str:thing_code>/release/", ThingReleaseView.as_view(), name="thing-release"),
    path("things/<str:thing_code>/request/", ThingRequestView.as_view(), name="thing-request"),
    path(
        "things/<str:thing_code>/calendar/",
        ThingCalendarView.as_view(),
        name="thing-calendar",
    ),
    # Bookings
    path("my-bookings/", MyBookingsView.as_view(), name="my-bookings"),
    path("owner-bookings/", OwnerBookingsView.as_view(), name="owner-bookings"),
    # FAQ
    path("things/<str:thing_code>/faq/", ThingFAQListView.as_view(), name="thing-faq-list"),
    path("faq/<str:faq_code>/", FAQDetailView.as_view(), name="faq-detail"),
    path("faq/<str:faq_code>/answer/", FAQAnswerView.as_view(), name="faq-answer"),
    path(
        "faq/<str:faq_code>/hide/",
        FAQVisibilityView.as_view(),
        {"action": "hide"},
        name="faq-hide",
    ),
    path(
        "faq/<str:faq_code>/show/",
        FAQVisibilityView.as_view(),
        {"action": "show"},
        name="faq-show",
    ),
]
