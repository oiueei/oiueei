"""
User model for OIUEEI.
"""

from datetime import date

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models

from core.utils import generate_id


class UserManager(BaseUserManager):
    """Custom manager for User model."""

    def create_user(self, user_email, **extra_fields):
        """Create and return a regular user."""
        if not user_email:
            raise ValueError("Email is required")
        user_email = self.normalize_email(user_email)
        user = self.model(user_email=user_email, **extra_fields)
        user.save(using=self._db)
        return user

    def create_superuser(self, user_email, **extra_fields):
        """Create and return a superuser."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(user_email, **extra_fields)


class User(AbstractBaseUser):
    """
    Custom User model with 6-character alphanumeric ID.
    Uses magic link authentication (no password).
    """

    user_code = models.CharField(max_length=6, primary_key=True, default=generate_id)
    user_email = models.CharField(max_length=64, unique=True)
    user_name = models.CharField(max_length=32, blank=True, default="")
    user_created = models.DateField(default=date.today)
    user_last_activity = models.DateField(default=date.today)
    user_own_collections = models.JSONField(default=list, blank=True)
    user_shared_collections = models.JSONField(default=list, blank=True)
    user_things = models.JSONField(default=list, blank=True)
    user_headline = models.CharField(max_length=64, blank=True, default="")
    user_thumbnail = models.CharField(max_length=16, blank=True, default="")
    user_hero = models.CharField(max_length=16, blank=True, default="")

    # Required for Django auth
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    password = None

    objects = UserManager()

    USERNAME_FIELD = "user_email"
    REQUIRED_FIELDS = []

    class Meta:
        app_label = "core"
        db_table = "users"

    def __str__(self):
        return f"{self.user_code} ({self.user_email})"

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser

    def update_last_activity(self):
        """Update the user's last activity date."""
        self.user_last_activity = date.today()
        self.save(update_fields=["user_last_activity"])
