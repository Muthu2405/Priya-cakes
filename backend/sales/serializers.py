from decimal import Decimal

from rest_framework import serializers

from products.models import Product

from .models import Sale, today


class OwnedProductField(serializers.PrimaryKeyRelatedField):
    """Only the signed-in user's own products can be chosen."""

    def get_queryset(self):
        request = self.context.get("request")
        return Product.objects.filter(owner=request.user) if request else Product.objects.none()


class SaleSerializer(serializers.ModelSerializer):
    product = OwnedProductField(required=False, allow_null=True)
    product_name = serializers.CharField(max_length=160, required=False, allow_blank=True)
    unit_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False, allow_null=True)
    in_catalog = serializers.SerializerMethodField()
    revenue = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    cost = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True, allow_null=True)
    profit = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True, allow_null=True)

    class Meta:
        model = Sale
        fields = ["id", "product", "product_name", "in_catalog", "sold_on", "quantity", "unit_price",
                  "unit_cost", "revenue", "cost", "profit", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_in_catalog(self, obj):
        return obj.product_id is not None

    def validate_product_name(self, value):
        return value.strip()

    def validate_sold_on(self, value):
        if value > today():
            raise serializers.ValidationError("A sale can't be dated in the future.")
        return value

    def validate(self, attrs):
        product = attrs.get("product")
        if product is not None:
            # Catalogue product: name and cost come from the product itself.
            attrs["product_name"] = product.name
            attrs["unit_cost"] = product.total_cost
        else:
            name = attrs.get("product_name") or (self.instance.product_name if self.instance and "product" not in attrs else "")
            if not name:
                raise serializers.ValidationError({"product_name": "Enter the product name."})
            attrs["product_name"] = name
            attrs.setdefault("unit_cost", None)
        return attrs
