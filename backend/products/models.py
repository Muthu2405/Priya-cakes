from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from ingredients.models import Ingredient, Unit


class SoldBy(models.TextChoices):
    PCS = "pcs", "pcs"
    KG = "kg", "kg"


class Product(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="products"
    )
    name = models.CharField(max_length=160)
    # Whether this product is sold by the piece or by weight (kg).
    sold_by = models.CharField(max_length=3, choices=SoldBy.choices, default=SoldBy.PCS)
    packaging_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    eb_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    labour_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_ingredient_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # Profit added on top of cost; defaults to 30% of the cost but the user can set any amount.
    profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def selling_price(self):
        return self.total_cost + self.profit

    def __str__(self):
        return self.name


class ProductIngredient(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="ingredients")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.PROTECT, related_name="product_lines")
    used_quantity = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal("0"))])
    used_unit = models.CharField(max_length=3, choices=Unit.choices)
    # Snapshot at save time: later price changes must not alter old costings.
    calculated_cost = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.product} - {self.ingredient.name}"
