# Generated manually - Data migration

from django.db import migrations


def create_default_theeeme(apps, schema_editor):
    """Create the default Barcelona theeeme."""
    Theeeme = apps.get_model("core", "Theeeme")
    Theeeme.objects.create(
        theeeme_code="BRCLON",
        theeeme_name="Barcelona",
        theeeme_010="FFFFFF",
        theeeme_020="F5F5F5",
        theeeme_040="E0E0E0",
        theeeme_060="BDBDBD",
        theeeme_080="9E9E9E",
        theeeme_100="757575",
        theeeme_200="616161",
        theeeme_400="424242",
        theeeme_600="212121",
        theeeme_800="000000",
    )


def reverse_default_theeeme(apps, schema_editor):
    """Remove the default Barcelona theeeme."""
    Theeeme = apps.get_model("core", "Theeeme")
    Theeeme.objects.filter(theeeme_code="BRCLON").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_theeeme"),
    ]

    operations = [
        migrations.RunPython(create_default_theeeme, reverse_default_theeeme),
    ]
