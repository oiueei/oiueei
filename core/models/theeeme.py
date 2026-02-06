"""
Theeeme model for OIUEEI.
"""

from django.db import models

from core.utils import generate_id


class Theeeme(models.Model):
    """
    A color palette theme for collections.
    Contains 6 color values (hex codes without #).
    """

    theeeme_code = models.CharField(max_length=6, primary_key=True, default=generate_id)
    theeeme_name = models.CharField(max_length=16)
    theeeme_01 = models.CharField(max_length=6)
    theeeme_02 = models.CharField(max_length=6)
    theeeme_03 = models.CharField(max_length=6)
    theeeme_04 = models.CharField(max_length=6)
    theeeme_05 = models.CharField(max_length=6)
    theeeme_06 = models.CharField(max_length=6)

    class Meta:
        app_label = "core"
        db_table = "theeemes"

    def __str__(self):
        return f"{self.theeeme_code}: {self.theeeme_name}"
