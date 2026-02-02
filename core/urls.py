"""
URL configuration for core app.
"""

from django.urls import path

from .views.auth import MeView, RequestLinkView, VerifyLinkView
from .views.collections import (
    CollectionDetailView,
    CollectionInviteView,
    CollectionListView,
    SharedCollectionsView,
)
from .views.faq import FAQAnswerView, FAQDetailView, ThingFAQListView
from .views.things import ThingDetailView, ThingListView, ThingReleaseView, ThingReserveView
from .views.users import UserDetailView

urlpatterns = [
    # Auth
    path("auth/request-link/", RequestLinkView.as_view(), name="request-link"),
    path("auth/verify/<str:rsvp_code>/", VerifyLinkView.as_view(), name="verify-link"),
    path("auth/me/", MeView.as_view(), name="me"),
    # Users
    path("users/<str:user_code>/", UserDetailView.as_view(), name="user-detail"),
    # Collections
    path("collections/", CollectionListView.as_view(), name="collection-list"),
    path("collections/shared/", SharedCollectionsView.as_view(), name="shared-collections"),
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
    path("things/<str:thing_code>/", ThingDetailView.as_view(), name="thing-detail"),
    path("things/<str:thing_code>/reserve/", ThingReserveView.as_view(), name="thing-reserve"),
    path("things/<str:thing_code>/release/", ThingReleaseView.as_view(), name="thing-release"),
    # FAQ
    path("things/<str:thing_code>/faq/", ThingFAQListView.as_view(), name="thing-faq-list"),
    path("faq/<str:faq_code>/", FAQDetailView.as_view(), name="faq-detail"),
    path("faq/<str:faq_code>/answer/", FAQAnswerView.as_view(), name="faq-answer"),
]
