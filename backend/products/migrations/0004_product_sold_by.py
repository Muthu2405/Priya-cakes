from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("products", "0003_labour_and_profit")]

    operations = [
        migrations.AddField(
            "product", "sold_by",
            models.CharField(choices=[("pcs", "pcs"), ("kg", "kg")], default="pcs", max_length=3),
        ),
    ]
