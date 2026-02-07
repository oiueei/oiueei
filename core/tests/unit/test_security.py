"""
Unit tests for OIUEEI security features.
"""

import string

from core.utils import generate_id


class TestSecureIdGeneration:
    """Tests for cryptographically secure ID generation."""

    def test_generate_id_length(self):
        """ID should be exactly 6 characters."""
        for _ in range(100):
            assert len(generate_id()) == 6

    def test_generate_id_characters(self):
        """ID should only contain uppercase letters and digits."""
        valid_chars = set(string.ascii_uppercase + string.digits)
        for _ in range(100):
            id_ = generate_id()
            assert all(c in valid_chars for c in id_)

    def test_generate_id_uniqueness(self):
        """IDs should be unique (statistically unlikely to collide in 1000 attempts)."""
        ids = set(generate_id() for _ in range(1000))
        # With 36^6 = 2.17 billion possibilities, 1000 IDs should be unique
        assert len(ids) == 1000

    def test_generate_id_uses_secrets_module(self):
        """Verify that secrets module is used (via inspection)."""
        import inspect

        from core import utils

        source = inspect.getsource(utils.generate_id)
        assert "secrets.choice" in source
        assert "random.choice" not in source
