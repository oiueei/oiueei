"""
FAQ model for OIUEEI.
"""

from django.db import models
from django.utils import timezone

from core.utils import generate_id


class FAQ(models.Model):
    """
    A question and answer for a thing.
    """

    faq_code = models.CharField(max_length=6, primary_key=True, default=generate_id)
    faq_thing = models.CharField(max_length=6)  # FK to Thing.thing_code
    faq_created = models.DateTimeField(default=timezone.now)
    faq_questioner = models.CharField(max_length=6)  # FK to User.user_code
    faq_question = models.CharField(max_length=64)
    faq_answer = models.CharField(max_length=256, blank=True, default="")
    faq_is_visible = models.BooleanField(default=True)

    class Meta:
        app_label = "core"
        db_table = "faqs"

    def __str__(self):
        return f"FAQ {self.faq_code}: {self.faq_question[:30]}..."

    def has_answer(self):
        """Check if this FAQ has been answered."""
        return bool(self.faq_answer)

    def answer(self, answer_text):
        """Set the answer for this FAQ."""
        self.faq_answer = answer_text
        self.save(update_fields=["faq_answer"])
