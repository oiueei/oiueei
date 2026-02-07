"""
Utility functions for OIUEEI.
"""

import secrets
import string

from django.conf import settings


def generate_id():
    """Generate a unique 6-character alphanumeric ID in uppercase."""
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(6))


def cloudinary_url(image_id):
    """Build Cloudinary URL from image ID."""
    if not image_id:
        return None
    cloud_name = getattr(settings, "CLOUDINARY_CLOUD_NAME", "oiueei")
    return f"https://res.cloudinary.com/{cloud_name}/image/upload/v1676535186/oiueei/{image_id}.png"
