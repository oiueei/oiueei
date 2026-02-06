# Generated manually

from django.db import migrations, models


def rename_article_to_thing(apps, schema_editor):
    """Rename GIFT_ARTICLE -> GIFT_THING, SELL_ARTICLE -> SELL_THING, etc."""
    Thing = apps.get_model("core", "Thing")
    mappings = {
        "GIFT_ARTICLE": "GIFT_THING",
        "SELL_ARTICLE": "SELL_THING",
        "ORDER_ARTICLE": "ORDER_THING",
        "RENT_ARTICLE": "RENT_THING",
        "LEND_ARTICLE": "LEND_THING",
        "SHARE_ARTICLE": "SHARE_THING",
    }
    for old_value, new_value in mappings.items():
        Thing.objects.filter(thing_type=old_value).update(thing_type=new_value)


def rename_thing_to_article(apps, schema_editor):
    """Reverse: GIFT_THING -> GIFT_ARTICLE, etc."""
    Thing = apps.get_model("core", "Thing")
    mappings = {
        "GIFT_THING": "GIFT_ARTICLE",
        "SELL_THING": "SELL_ARTICLE",
        "ORDER_THING": "ORDER_ARTICLE",
        "RENT_THING": "RENT_ARTICLE",
        "LEND_THING": "LEND_ARTICLE",
        "SHARE_THING": "SHARE_ARTICLE",
    }
    for old_value, new_value in mappings.items():
        Thing.objects.filter(thing_type=old_value).update(thing_type=new_value)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_rename_collection_articles"),
    ]

    operations = [
        migrations.AlterField(
            model_name="thing",
            name="thing_type",
            field=models.CharField(
                choices=[
                    ("GIFT_THING", "Gift Thing"),
                    ("SELL_THING", "Sell Thing"),
                    ("ORDER_THING", "Order Thing"),
                    ("RENT_THING", "Rent Thing"),
                    ("LEND_THING", "Lend Thing"),
                    ("SHARE_THING", "Share Thing"),
                ],
                default="GIFT_THING",
                max_length=16,
            ),
        ),
        migrations.RunPython(rename_article_to_thing, rename_thing_to_article),
    ]
