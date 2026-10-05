from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from products.models import Product


def today():
    return timezone.localdate()


class Sale(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sales")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="sales")
    sold_on = models.DateField(default=today, db_index=True)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    # Snapshot of the product's cost when the sale was recorded, so later
    # re-costing never rewrites past profit.
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sold_on", "-id"]

    @property
    def revenue(self):
        return self.unit_price * self.quantity

    @property
    def cost(self):
        return self.unit_cost * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product} on {self.sold_on}"
