# Generated manually

from django.db import migrations, models

import core.utils


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Theeeme",
            fields=[
                (
                    "theeeme_code",
                    models.CharField(
                        default=core.utils.generate_id,
                        max_length=6,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("theeeme_name", models.CharField(max_length=16)),
                ("theeeme_010", models.CharField(max_length=6)),
                ("theeeme_020", models.CharField(max_length=6)),
                ("theeeme_040", models.CharField(max_length=6)),
                ("theeeme_060", models.CharField(max_length=6)),
                ("theeeme_080", models.CharField(max_length=6)),
                ("theeeme_100", models.CharField(max_length=6)),
                ("theeeme_200", models.CharField(max_length=6)),
                ("theeeme_400", models.CharField(max_length=6)),
                ("theeeme_600", models.CharField(max_length=6)),
                ("theeeme_800", models.CharField(max_length=6)),
            ],
            options={
                "db_table": "theeemes",
            },
        ),
    ]
