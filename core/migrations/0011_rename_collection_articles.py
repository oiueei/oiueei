# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_rename_user_shared_collections"),
    ]

    operations = [
        migrations.RenameField(
            model_name="collection",
            old_name="collection_articles",
            new_name="collection_things",
        ),
    ]
