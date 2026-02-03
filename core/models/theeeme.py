"""
Theeeme model for OIUEEI.
"""

from django.db import models

from core.utils import generate_id


class Theeeme(models.Model):
    """
    A color palette theme for collections.
    Contains 10 color values (hex codes without #).
    """

    theeeme_code = models.CharField(max_length=6, primary_key=True, default=generate_id)
    theeeme_name = models.CharField(max_length=16)
    theeeme_010 = models.CharField(max_length=6)
    theeeme_020 = models.CharField(max_length=6)
    theeeme_040 = models.CharField(max_length=6)
    theeeme_060 = models.CharField(max_length=6)
    theeeme_080 = models.CharField(max_length=6)
    theeeme_100 = models.CharField(max_length=6)
    theeeme_200 = models.CharField(max_length=6)
    theeeme_400 = models.CharField(max_length=6)
    theeeme_600 = models.CharField(max_length=6)
    theeeme_800 = models.CharField(max_length=6)

    class Meta:
        app_label = "core"
        db_table = "theeemes"

    def __str__(self):
        return f"{self.theeeme_code}: {self.theeeme_name}"
