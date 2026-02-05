"""
URL configuration for core app.
"""

from django.urls import path

from .views.auth import LogoutView, MeView, RequestLinkView, VerifyLinkView
from .views.booking import (
    BookingAcceptView,
    BookingRejectView,
    MyBookingsView,
    OwnerBookingsView,
    ThingCalendarView,
)
from .views.collections import (
    CollectionDetailView,
    CollectionInviteView,
    CollectionListView,
    InvitedCollectionsView,
)
from .views.faq import FAQAnswerView, FAQDetailView, ThingFAQListView
from .views.reservations import ReservationAcceptView, ReservationRejectView, ThingRequestView
from .views.things import (
    InvitedThingsView,
    ThingDetailView,
    ThingListView,
    ThingReleaseView,
    ThingReserveView,
)
from .views.users import UserDetailView

urlpatterns = [
    # Auth
    path("auth/request-link/", RequestLinkView.as_view(), name="request-link"),
    path("auth/verify/<str:rsvp_code>/", VerifyLinkView.as_view(), name="verify-link"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
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
    # Reservations (standard flow for GIFT/SELL/ORDER)
    path(
        "reservations/<str:reservation_code>/accept/",
        ReservationAcceptView.as_view(),
        name="reservation-accept",
    ),
    path(
        "reservations/<str:reservation_code>/reject/",
        ReservationRejectView.as_view(),
        name="reservation-reject",
    ),
    # Bookings (date-based flow for LEND/RENT/SHARE)
    path(
        "bookings/<str:booking_code>/accept/",
        BookingAcceptView.as_view(),
        name="booking-accept",
    ),
    path(
        "bookings/<str:booking_code>/reject/",
        BookingRejectView.as_view(),
        name="booking-reject",
    ),
    path("my-bookings/", MyBookingsView.as_view(), name="my-bookings"),
    path("owner-bookings/", OwnerBookingsView.as_view(), name="owner-bookings"),
    # FAQ
    path("things/<str:thing_code>/faq/", ThingFAQListView.as_view(), name="thing-faq-list"),
    path("faq/<str:faq_code>/", FAQDetailView.as_view(), name="faq-detail"),
    path("faq/<str:faq_code>/answer/", FAQAnswerView.as_view(), name="faq-answer"),
]
