"""
Django Admin configuration for OIUEEI.
"""

from django.contrib import admin

from core.models import FAQ, RSVP, Collection, Theeeme, Thing, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["user_code", "user_email", "user_name", "user_created"]
    search_fields = ["user_code", "user_email", "user_name"]


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = [
        "collection_code",
        "collection_headline",
        "collection_owner",
        "collection_status",
    ]
    search_fields = ["collection_code", "collection_headline"]
    list_filter = ["collection_status", "collection_theeeme"]


@admin.register(Thing)
class ThingAdmin(admin.ModelAdmin):
    list_display = [
        "thing_code",
        "thing_headline",
        "thing_owner",
        "thing_type",
        "thing_status",
    ]
    search_fields = ["thing_code", "thing_headline"]
    list_filter = ["thing_type", "thing_status", "thing_available"]


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ["faq_code", "faq_question", "faq_thing", "faq_is_visible"]
    search_fields = ["faq_code", "faq_question"]
    list_filter = ["faq_is_visible"]


@admin.register(RSVP)
class RSVPAdmin(admin.ModelAdmin):
    list_display = ["rsvp_code", "user_email", "user_code", "rsvp_created"]
    search_fields = ["rsvp_code", "user_email"]


@admin.register(Theeeme)
class TheeemeAdmin(admin.ModelAdmin):
    list_display = ["theeeme_code", "theeeme_name"]
    search_fields = ["theeeme_code", "theeeme_name"]
