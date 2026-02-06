"""
BookingPeriod model - unified reservation/booking model for all thing types.

This model handles all reservation scenarios:
- GIFT_THING, SELL_THING: Single-use reservations (no dates, thing becomes INACTIVE)
- ORDER_THING: Repeatable orders (delivery_date + quantity, thing stays ACTIVE)
- LEND_THING, RENT_THING, SHARE_THING: Date-based bookings (start/end dates, thing stays ACTIVE)
"""

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.utils import generate_id

# Thing types that require dates for booking
DATE_BASED_TYPES = ["LEND_THING", "RENT_THING", "SHARE_THING"]

# Thing types where the thing becomes unavailable after acceptance
SINGLE_USE_TYPES = ["GIFT_THING", "SELL_THING"]

# Thing types that can be ordered repeatedly (always available)
REPEATABLE_TYPES = ["ORDER_THING"]


class BookingPeriod(models.Model):
    """
    Unified reservation/booking model for all thing types.

    For GIFT/SELL: no dates required
    For ORDER: delivery_date and quantity required
    For LEND/RENT/SHARE: start_date and end_date required

    The thing_type field determines behavior on acceptance:
    - GIFT/SELL: thing.thing_status -> INACTIVE, thing.thing_available -> False
    - ORDER: thing stays ACTIVE (can be ordered again)
    - LEND/RENT/SHARE: thing stays ACTIVE (date-based availability)
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
    thing_type = models.CharField(max_length=12, default="GIFT_THING")  # To know how to handle
    requester_code = models.CharField(max_length=6)
    requester_email = models.CharField(max_length=64)
    owner_code = models.CharField(max_length=6)
    start_date = models.DateField(null=True, blank=True)  # For LEND/RENT/SHARE
    end_date = models.DateField(null=True, blank=True)  # For LEND/RENT/SHARE
    delivery_date = models.DateField(null=True, blank=True)  # For ORDER_THING
    quantity = models.PositiveIntegerField(null=True, blank=True)  # For ORDER_THING
    status = models.CharField(max_length=8, choices=STATUS_CHOICES, default="PENDING")

    class Meta:
        app_label = "core"
        db_table = "booking_periods"

    def __str__(self):
        if self.start_date and self.end_date:
            return (
                f"Booking {self.booking_code} for {self.thing_code} "
                f"({self.start_date} - {self.end_date})"
            )
        if self.delivery_date:
            qty = f"x{self.quantity}" if self.quantity else ""
            return (
                f"Order {self.booking_code} for {self.thing_code} "
                f"(delivery: {self.delivery_date}) {qty}"
            )
        return f"Booking {self.booking_code} for {self.thing_code}"

    def is_date_based(self):
        """Check if this booking requires dates (LEND/RENT/SHARE)."""
        return self.thing_type in DATE_BASED_TYPES

    def is_single_use(self):
        """Check if this booking makes the thing unavailable (GIFT/SELL)."""
        return self.thing_type in SINGLE_USE_TYPES

    def is_repeatable(self):
        """Check if this thing can be ordered repeatedly (ORDER)."""
        return self.thing_type in REPEATABLE_TYPES

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
