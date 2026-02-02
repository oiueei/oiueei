"""
RSVP model for magic link authentication.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.utils import generate_id


class RSVP(models.Model):
    """
    Magic link token for passwordless authentication.
    Expires after MAGIC_LINK_EXPIRY_HOURS (default 24 hours).
    """

    rsvp_code = models.CharField(max_length=6, primary_key=True, default=generate_id)
    rsvp_created = models.DateTimeField(default=timezone.now)
    user_code = models.CharField(max_length=6)
    user_email = models.CharField(max_length=64)

    class Meta:
        app_label = "core"
        db_table = "rsvps"

    def __str__(self):
        return f"RSVP {self.rsvp_code} for {self.user_email}"

    def is_valid(self):
        """Check if the RSVP is still valid (not expired)."""
        from datetime import timedelta

        expiry_hours = getattr(settings, "MAGIC_LINK_EXPIRY_HOURS", 24)
        expiry_time = self.rsvp_created + timedelta(hours=expiry_hours)
        return timezone.now() < expiry_time
