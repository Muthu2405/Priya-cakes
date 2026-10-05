import django.db.models.deletion
from django.db import migrations, models


def copy_names(apps, schema_editor):
    Sale = apps.get_model("sales", "Sale")
    for s in Sale.objects.select_related("product"):
        s.product_name = s.product.name if s.product_id else ""
        s.save(update_fields=["product_name"])


class Migration(migrations.Migration):
    dependencies = [("sales", "0001_initial"), ("products", "0003_labour_and_profit")]

    operations = [
        migrations.AddField("sale", "product_name", models.CharField(default="", max_length=160), preserve_default=False),
        migrations.RunPython(copy_names, migrations.RunPython.noop),
        migrations.AlterField(
            "sale", "product",
            models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                              related_name="sales", to="products.product"),
        ),
        migrations.AlterField(
            "sale", "unit_cost", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
    ]
