# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_bookingperiod"),
    ]

    operations = [
        migrations.RenameField(
            model_name="user",
            old_name="user_shared_collections",
            new_name="user_invited_collections",
        ),
    ]
