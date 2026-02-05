"""
ReservationRequest model for OIUEEI.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.utils import generate_id


class ReservationRequest(models.Model):
    """
    A reservation request for a thing.
    Created when an invited user requests to reserve a thing.
    Owner must accept or reject via email links.
    """

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ACCEPTED", "Accepted"),
        ("REJECTED", "Rejected"),
    ]

    reservation_code = models.CharField(max_length=6, primary_key=True, default=generate_id)
    reservation_created = models.DateTimeField(default=timezone.now)
    thing_code = models.CharField(max_length=6)
    requester_code = models.CharField(max_length=6)  # User who requested
    requester_email = models.CharField(max_length=64)
    owner_code = models.CharField(max_length=6)  # Thing owner
    status = models.CharField(max_length=8, choices=STATUS_CHOICES, default="PENDING")

    class Meta:
        app_label = "core"
        db_table = "reservation_requests"

    def __str__(self):
        return f"Reservation {self.reservation_code} for {self.thing_code}"

    def is_valid(self):
        """Check if the reservation request is still valid (not expired)."""
        from datetime import timedelta

        expiry_hours = getattr(settings, "RESERVATION_EXPIRY_HOURS", 72)
        expiry_time = self.reservation_created + timedelta(hours=expiry_hours)
        return timezone.now() < expiry_time and self.status == "PENDING"

    def accept(self):
        """Accept the reservation request."""
        self.status = "ACCEPTED"
        self.save(update_fields=["status"])

    def reject(self):
        """Reject the reservation request."""
        self.status = "REJECTED"
        self.save(update_fields=["status"])
