"""
Thing model for OIUEEI.
"""

from django.db import models
from django.utils import timezone

from core.utils import generate_id


class Thing(models.Model):
    """
    An item in a collection (gift, sale item, or order).
    """

    TYPE_CHOICES = [
        ("GIFT_ARTICLE", "Gift Article"),
        ("SELL_ARTICLE", "Sell Article"),
        ("ORDER_ARTICLE", "Order Article"),
    ]

    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
        ("TAKEN", "Taken"),
    ]

    thing_code = models.CharField(max_length=6, primary_key=True, default=generate_id)
    thing_type = models.CharField(max_length=16, choices=TYPE_CHOICES, default="GIFT_ARTICLE")
    thing_owner = models.CharField(max_length=6)  # FK to User.user_code
    thing_created = models.DateTimeField(default=timezone.now)
    thing_headline = models.CharField(max_length=64)
    thing_description = models.CharField(max_length=256, blank=True, default="")
    thing_thumbnail = models.CharField(max_length=16, blank=True, default="")
    thing_pictures = models.JSONField(default=list, blank=True)  # Array of image IDs
    thing_status = models.CharField(max_length=8, choices=STATUS_CHOICES, default="ACTIVE")
    thing_faq = models.JSONField(default=list, blank=True)  # Array of faq_codes
    thing_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    thing_deal = models.JSONField(default=list, blank=True)  # Array of user_codes who reserved
    thing_available = models.BooleanField(default=True)

    class Meta:
        app_label = "core"
        db_table = "things"

    def __str__(self):
        return f"{self.thing_code}: {self.thing_headline}"

    def is_owner(self, user_code):
        """Check if the given user is the owner."""
        return self.thing_owner == user_code

    def reserve(self, user_code):
        """Reserve this thing for a user."""
        if user_code not in self.thing_deal:
            self.thing_deal.append(user_code)
            self.thing_available = False
            self.save(update_fields=["thing_deal", "thing_available"])

    def release(self, user_code):
        """Release a user's reservation."""
        if user_code in self.thing_deal:
            self.thing_deal.remove(user_code)
            if not self.thing_deal:
                self.thing_available = True
            self.save(update_fields=["thing_deal", "thing_available"])

    def add_faq(self, faq_code):
        """Add a FAQ to this thing."""
        if faq_code not in self.thing_faq:
            self.thing_faq.append(faq_code)
            self.save(update_fields=["thing_faq"])

    def remove_faq(self, faq_code):
        """Remove a FAQ from this thing."""
        if faq_code in self.thing_faq:
            self.thing_faq.remove(faq_code)
            self.save(update_fields=["thing_faq"])
