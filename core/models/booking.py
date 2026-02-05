"""
BookingPeriod model for date-based lending calendar.
"""

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.utils import generate_id


class BookingPeriod(models.Model):
    """
    A booking period for lend/rent/share things.
    Represents a date range when a thing is reserved or requested.
    """

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ACCEPTED", "Accepted"),
        ("REJECTED", "Rejected"),
        ("EXPIRED", "Expired"),
    ]

    booking_code = models.CharField(max_length=6, primary_key=True, default=generate_id)
    booking_created = models.DateTimeField(default=timezone.now)
    thing_code = models.CharField(max_length=6, db_index=True)
    requester_code = models.CharField(max_length=6)
    requester_email = models.CharField(max_length=64)
    owner_code = models.CharField(max_length=6)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=8, choices=STATUS_CHOICES, default="PENDING")

    class Meta:
        app_label = "core"
        db_table = "booking_periods"

    def __str__(self):
        return (
            f"Booking {self.booking_code} for {self.thing_code} "
            f"({self.start_date} - {self.end_date})"
        )

    def is_valid(self):
        """Check if the booking request is still valid (not expired and PENDING)."""
        expiry_hours = getattr(settings, "BOOKING_EXPIRY_HOURS", 72)
        expiry_time = self.booking_created + timedelta(hours=expiry_hours)
        return timezone.now() < expiry_time and self.status == "PENDING"

    def accept(self):
        """Accept the booking request."""
        self.status = "ACCEPTED"
        self.save(update_fields=["status"])

    def reject(self):
        """Reject the booking request."""
        self.status = "REJECTED"
        self.save(update_fields=["status"])

    def expire(self):
        """Mark the booking as expired."""
        self.status = "EXPIRED"
        self.save(update_fields=["status"])

    @classmethod
    def has_overlap(cls, thing_code, start_date, end_date, exclude_booking_code=None):
        """
        Check if there's an overlap with existing PENDING or ACCEPTED bookings.

        Overlap exists when:
        existing.start_date <= requested.end_date AND existing.end_date >= requested.start_date
        """
        queryset = cls.objects.filter(
            thing_code=thing_code,
            status__in=["PENDING", "ACCEPTED"],
            start_date__lte=end_date,
            end_date__gte=start_date,
        )
        if exclude_booking_code:
            queryset = queryset.exclude(booking_code=exclude_booking_code)
        return queryset.exists()

    @classmethod
    def get_blocked_periods(cls, thing_code):
        """
        Get all blocked periods for a thing (PENDING and ACCEPTED bookings).
        Returns queryset of BookingPeriod objects.
        """
        return cls.objects.filter(
            thing_code=thing_code,
            status__in=["PENDING", "ACCEPTED"],
        ).order_by("start_date")

    @classmethod
    def expire_old_pending(cls):
        """
        Expire all PENDING bookings that have passed the expiry time.
        Useful for batch processing/cleanup.
        """
        expiry_hours = getattr(settings, "BOOKING_EXPIRY_HOURS", 72)
        cutoff_time = timezone.now() - timedelta(hours=expiry_hours)
        expired_count = cls.objects.filter(
            status="PENDING",
            booking_created__lt=cutoff_time,
        ).update(status="EXPIRED")
        return expired_count
