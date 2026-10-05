from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from ingredients.models import Ingredient, Unit

from .models import Product, ProductIngredient, SoldBy
from .services import IncompatibleUnitsError, calculate_product

MONEY = dict(max_digits=12, decimal_places=2, min_value=Decimal("0"), default=0)


class OwnedIngredientField(serializers.PrimaryKeyRelatedField):
    """Only the signed-in user's active ingredients can be chosen."""

    def get_queryset(self):
        request = self.context.get("request")
        qs = Ingredient.objects.filter(active=True)
        return qs.filter(owner=request.user) if request else qs.none()


class ProductIngredientSerializer(serializers.ModelSerializer):
    ingredient = OwnedIngredientField()
    ingredient_name = serializers.CharField(source="ingredient.name", read_only=True)
    used_quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0"))
    used_unit = serializers.ChoiceField(choices=Unit.choices)

    class Meta:
        model = ProductIngredient
        fields = ["id", "ingredient", "ingredient_name", "used_quantity", "used_unit", "calculated_cost"]
        read_only_fields = ["calculated_cost"]


class ProductSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=160)
    sold_by = serializers.ChoiceField(choices=SoldBy.choices, default=SoldBy.PCS)
    packaging_cost = serializers.DecimalField(**MONEY)
    eb_cost = serializers.DecimalField(**MONEY)
    labour_cost = serializers.DecimalField(**MONEY)
    # Optional: left out, it becomes 30% of the cost.
    profit = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False)
    selling_price = serializers.DecimalField(max_digits=13, decimal_places=2, read_only=True)
    ingredients = ProductIngredientSerializer(many=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "sold_by", "packaging_cost", "eb_cost", "labour_cost",
            "total_ingredient_cost", "total_cost", "profit", "selling_price",
            "ingredients", "created_at", "updated_at",
        ]
        read_only_fields = ["total_ingredient_cost", "total_cost", "created_at", "updated_at"]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Product name cannot be empty.")
        return value

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError("A product must contain at least one ingredient.")
        return value

    def validate(self, attrs):
        try:
            attrs["_computed"] = calculate_product(
                attrs["ingredients"],
                attrs["packaging_cost"],
                attrs["eb_cost"],
                attrs["labour_cost"],
                attrs.get("profit"),
            )
        except IncompatibleUnitsError as exc:
            raise serializers.ValidationError({"ingredients": str(exc)})
        return attrs

    def _save(self, product, validated):
        computed = validated.pop("_computed")
        validated.pop("ingredients")
        for field, value in validated.items():
            setattr(product, field, value)
        product.packaging_cost = computed["packaging_cost"]
        product.eb_cost = computed["eb_cost"]
        product.labour_cost = computed["labour_cost"]
        product.profit = computed["profit"]
        product.total_ingredient_cost = computed["total_ingredient_cost"]
        product.total_cost = computed["total_cost"]
        product.save()
        product.ingredients.all().delete()
        ProductIngredient.objects.bulk_create([
            ProductIngredient(
                product=product,
                ingredient=line["ingredient"],
                used_quantity=line["used_quantity"],
                used_unit=line["used_unit"],
                calculated_cost=line["calculated_cost"],
            )
            for line in computed["lines"]
        ])
        return product

    @transaction.atomic
    def create(self, validated_data):
        return self._save(Product(), validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        return self._save(instance, validated_data)
