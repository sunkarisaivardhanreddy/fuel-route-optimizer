from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="FuelStation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("opis_id", models.BigIntegerField(unique=True)),
                ("name", models.CharField(max_length=255)),
                ("address", models.CharField(blank=True, max_length=255)),
                ("city", models.CharField(max_length=100)),
                ("state", models.CharField(max_length=2)),
                ("rack_id", models.IntegerField(blank=True, null=True)),
                ("retail_price", models.DecimalField(decimal_places=4, max_digits=8)),
                ("latitude", models.FloatField(blank=True, null=True)),
                ("longitude", models.FloatField(blank=True, null=True)),
                ("geocode_source", models.CharField(blank=True, max_length=40)),
                ("geocoded_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "indexes": [
                    models.Index(fields=["state", "city"], name="routes_fuelst_state_cit_1fbbd3_idx"),
                    models.Index(fields=["retail_price"], name="routes_fuelst_retail__b30a0e_idx"),
                ],
            },
        ),
    ]
