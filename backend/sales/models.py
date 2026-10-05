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
    # Set when the sold item is one of the user's products; empty for a one-off item
    # typed in by hand, or after the product was deleted. The name is always kept.
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL, related_name="sales")
    product_name = models.CharField(max_length=160)
    sold_on = models.DateField(default=today, db_index=True)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    # Snapshot of the product's cost when the sale was recorded, so later re-costing
    # never rewrites past profit. Empty when the cost of a one-off item isn't known.
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sold_on", "-id"]

    @property
    def revenue(self):
        return self.unit_price * self.quantity

    @property
    def cost(self):
        return None if self.unit_cost is None else self.unit_cost * self.quantity

    @property
    def profit(self):
        return None if self.unit_cost is None else self.revenue - self.cost

    def __str__(self):
        return f"{self.quantity} x {self.product_name} on {self.sold_on}"
