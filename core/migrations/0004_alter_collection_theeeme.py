# Generated manually

from django.db import migrations, models
import django.db.models.deletion


def set_default_theeeme(apps, schema_editor):
    """Set the default theeeme for all existing collections."""
    Collection = apps.get_model("core", "Collection")
    Collection.objects.all().update(collection_theeeme="BRCLON")


def reverse_set_default_theeeme(apps, schema_editor):
    """Revert to the old default value."""
    Collection = apps.get_model("core", "Collection")
    Collection.objects.all().update(collection_theeeme="BAR_CEL_ONA")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_create_default_theeeme"),
    ]

    operations = [
        # First, update existing collections to use the new theeeme code
        migrations.RunPython(set_default_theeeme, reverse_set_default_theeeme),
        # Then alter the field to be a ForeignKey
        migrations.AlterField(
            model_name="collection",
            name="collection_theeeme",
            field=models.ForeignKey(
                db_column="collection_theeeme",
                on_delete=django.db.models.deletion.PROTECT,
                to="core.theeeme",
                to_field="theeeme_code",
            ),
        ),
    ]
