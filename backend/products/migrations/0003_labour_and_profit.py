from decimal import ROUND_HALF_UP, Decimal

from django.db import migrations, models


def backfill_profit(apps, schema_editor):
    """Existing products get the same 30% default new ones do."""
    Product = apps.get_model("products", "Product")
    for p in Product.objects.all():
        p.profit = (p.total_cost * Decimal("0.30")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        p.save(update_fields=["profit"])


class Migration(migrations.Migration):
    dependencies = [("products", "0002_remove_product_cost_per_piece_and_more")]

    operations = [
        migrations.RenameField("product", "other_cost", "labour_cost"),
        migrations.AddField(
            "product", "profit", models.DecimalField(decimal_places=2, default=0, max_digits=12)
        ),
        migrations.RunPython(backfill_profit, migrations.RunPython.noop),
    ]
