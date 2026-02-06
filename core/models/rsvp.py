"""
RSVP model for magic link authentication and action intermediary.

RSVP serves as an intermediary for ALL email communications to avoid
exposing real codes (thing_code, booking_code, etc.) in URLs.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.utils import generate_id


class RSVP(models.Model):
    """
    Magic link token for passwordless authentication and action intermediary.

    Used for:
    - MAGIC_LINK: Passwordless authentication
    - COLLECTION_INVITE: Invitation to view a collection
    - RESERVATION_ACCEPT: Accept a reservation request (GIFT/SELL/ORDER)
    - RESERVATION_REJECT: Reject a reservation request
    - BOOKING_ACCEPT: Accept a booking period (LEND/RENT/SHARE)
    - BOOKING_REJECT: Reject a booking period

    Expires after MAGIC_LINK_EXPIRY_HOURS (default 24 hours).
    Deleted after one-time use.
    """

    ACTION_CHOICES = [
        ("MAGIC_LINK", "Magic Link"),
        ("COLLECTION_INVITE", "Collection Invite"),
        ("BOOKING_ACCEPT", "Booking Accept"),
        ("BOOKING_REJECT", "Booking Reject"),
    ]

    rsvp_code = models.CharField(max_length=6, primary_key=True, default=generate_id)
    rsvp_created = models.DateTimeField(default=timezone.now)
    user_code = models.CharField(max_length=6)
    user_email = models.CharField(max_length=64)

    # Action type and target
    rsvp_action = models.CharField(max_length=20, choices=ACTION_CHOICES, default="MAGIC_LINK")
    rsvp_target_code = models.CharField(max_length=6, null=True, blank=True)

    # Legacy field for collection invites (maintained for backwards compatibility)
    collection_code = models.CharField(max_length=6, null=True, blank=True)

    # Additional context data (JSON) for the action
    rsvp_context = models.JSONField(default=dict, blank=True)

    class Meta:
        app_label = "core"
        db_table = "rsvps"

    def __str__(self):
        return f"RSVP {self.rsvp_code} ({self.rsvp_action}) for {self.user_email}"

    def is_valid(self):
        """Check if the RSVP is still valid (not expired)."""
        from datetime import timedelta

        expiry_hours = getattr(settings, "MAGIC_LINK_EXPIRY_HOURS", 24)
        expiry_time = self.rsvp_created + timedelta(hours=expiry_hours)
        return timezone.now() < expiry_time

    @classmethod
    def create_for_booking(cls, action, booking, owner_email):
        """
        Create an RSVP for a booking accept/reject action.

        Args:
            action: 'BOOKING_ACCEPT' or 'BOOKING_REJECT'
            booking: BookingPeriod instance
            owner_email: Email of the owner to send the link to
        """
        context = {
            "thing_code": booking.thing_code,
            "thing_type": booking.thing_type,
            "requester_code": booking.requester_code,
            "requester_email": booking.requester_email,
        }
        # Include dates if they exist (for LEND/RENT/SHARE)
        if booking.start_date:
            context["start_date"] = str(booking.start_date)
        if booking.end_date:
            context["end_date"] = str(booking.end_date)
        # Include order info if it exists (for ORDER_THING)
        if booking.delivery_date:
            context["delivery_date"] = str(booking.delivery_date)
        if booking.quantity:
            context["quantity"] = booking.quantity

        return cls.objects.create(
            user_code=booking.owner_code,
            user_email=owner_email,
            rsvp_action=action,
            rsvp_target_code=booking.booking_code,
            rsvp_context=context,
        )
