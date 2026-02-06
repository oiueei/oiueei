# Generated manually

from django.db import migrations, models


def update_default_theeeme(apps, schema_editor):
    """Update the default theeeme to BAR_CEL_ONA."""
    Theeeme = apps.get_model("core", "Theeeme")
    Collection = apps.get_model("core", "Collection")

    # Create new default theeeme first
    new_theeeme = Theeeme.objects.create(
        theeeme_code="JMPA01",
        theeeme_name="BAR_CEL_ONA",
        theeeme_01="FFCA2C",
        theeeme_02="CB4E22",
        theeeme_03="827F2A",
        theeeme_04="2B9A9E",
        theeeme_05="4F3B28",
        theeeme_06="FFF2EB",
    )

    # Update all collections to use new theeeme BEFORE deleting old one
    Collection.objects.filter(collection_theeeme="BRCLON").update(
        collection_theeeme="JMPA01"
    )

    # Now safe to delete old theeeme
    Theeeme.objects.filter(theeeme_code="BRCLON").delete()


def reverse_update_default_theeeme(apps, schema_editor):
    """Restore the old Barcelona theeeme."""
    Theeeme = apps.get_model("core", "Theeeme")
    Collection = apps.get_model("core", "Collection")

    # Recreate old theeeme first
    Theeeme.objects.create(
        theeeme_code="BRCLON",
        theeeme_name="Barcelona",
        theeeme_01="FFFFFF",
        theeeme_02="F5F5F5",
        theeeme_03="E0E0E0",
        theeeme_04="BDBDBD",
        theeeme_05="9E9E9E",
        theeeme_06="757575",
    )

    # Update all collections back
    Collection.objects.filter(collection_theeeme="JMPA01").update(
        collection_theeeme="BRCLON"
    )

    # Delete new theeeme
    Theeeme.objects.filter(theeeme_code="JMPA01").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_rename_thing_types"),
    ]

    operations = [
        # Remove old color fields
        migrations.RemoveField(model_name="theeeme", name="theeeme_010"),
        migrations.RemoveField(model_name="theeeme", name="theeeme_020"),
        migrations.RemoveField(model_name="theeeme", name="theeeme_040"),
        migrations.RemoveField(model_name="theeeme", name="theeeme_060"),
        migrations.RemoveField(model_name="theeeme", name="theeeme_080"),
        migrations.RemoveField(model_name="theeeme", name="theeeme_100"),
        migrations.RemoveField(model_name="theeeme", name="theeeme_200"),
        migrations.RemoveField(model_name="theeeme", name="theeeme_400"),
        migrations.RemoveField(model_name="theeeme", name="theeeme_600"),
        migrations.RemoveField(model_name="theeeme", name="theeeme_800"),
        # Add new color fields
        migrations.AddField(
            model_name="theeeme",
            name="theeeme_01",
            field=models.CharField(max_length=6, default="000000"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="theeeme",
            name="theeeme_02",
            field=models.CharField(max_length=6, default="000000"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="theeeme",
            name="theeeme_03",
            field=models.CharField(max_length=6, default="000000"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="theeeme",
            name="theeeme_04",
            field=models.CharField(max_length=6, default="000000"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="theeeme",
            name="theeeme_05",
            field=models.CharField(max_length=6, default="000000"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="theeeme",
            name="theeeme_06",
            field=models.CharField(max_length=6, default="000000"),
            preserve_default=False,
        ),
        # Update data (create new, update collections, then delete old)
        migrations.RunPython(update_default_theeeme, reverse_update_default_theeeme),
    ]
