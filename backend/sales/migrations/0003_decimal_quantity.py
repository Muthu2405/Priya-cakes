import django.core.validators
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("sales", "0002_unlisted_products")]

    operations = [
        migrations.AlterField(
            "sale", "quantity",
            models.DecimalField(
                decimal_places=3, max_digits=12,
                validators=[django.core.validators.MinValueValidator(Decimal("0.001"))],
            ),
        ),
    ]
