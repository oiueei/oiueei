"""
Collection model for OIUEEI.
"""

from django.db import models
from django.utils import timezone

from core.utils import generate_id


class Collection(models.Model):
    """
    A collection of things (gifts, sales, orders) owned by a user.
    Can be shared with other users via invites.
    """

    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
    ]

    collection_code = models.CharField(max_length=6, primary_key=True, default=generate_id)
    collection_owner = models.CharField(max_length=6)  # FK to User.user_code
    collection_created = models.DateTimeField(default=timezone.now)
    collection_headline = models.CharField(max_length=64)
    collection_description = models.CharField(max_length=256, blank=True, default="")
    collection_thumbnail = models.CharField(max_length=16, blank=True, default="")
    collection_hero = models.CharField(max_length=16, blank=True, default="")
    collection_status = models.CharField(max_length=8, choices=STATUS_CHOICES, default="ACTIVE")
    collection_things = models.JSONField(default=list, blank=True)  # Array of thing_codes
    collection_invites = models.JSONField(default=list, blank=True)  # Array of user_codes
    collection_theeeme = models.ForeignKey(
        "Theeeme",
        on_delete=models.PROTECT,
        to_field="theeeme_code",
        db_column="collection_theeeme",
    )

    class Meta:
        app_label = "core"
        db_table = "collections"

    def __str__(self):
        return f"{self.collection_code}: {self.collection_headline}"

    def add_thing(self, thing_code):
        """Add a thing to this collection."""
        if thing_code not in self.collection_things:
            self.collection_things.append(thing_code)
            self.save(update_fields=["collection_things"])

    def remove_thing(self, thing_code):
        """Remove a thing from this collection."""
        if thing_code in self.collection_things:
            self.collection_things.remove(thing_code)
            self.save(update_fields=["collection_things"])

    def add_invite(self, user_code):
        """Add a user to the invites list."""
        if user_code not in self.collection_invites:
            self.collection_invites.append(user_code)
            self.save(update_fields=["collection_invites"])

    def remove_invite(self, user_code):
        """Remove a user from the invites list."""
        if user_code in self.collection_invites:
            self.collection_invites.remove(user_code)
            self.save(update_fields=["collection_invites"])

    def is_owner(self, user_code):
        """Check if the given user is the owner."""
        return self.collection_owner == user_code

    def is_invited(self, user_code):
        """Check if the given user is invited."""
        return user_code in self.collection_invites

    def can_view(self, user_code):
        """Check if the given user can view this collection."""
        return self.is_owner(user_code) or self.is_invited(user_code)
