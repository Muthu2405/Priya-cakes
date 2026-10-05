from rest_framework import serializers

from products.models import Product

from .models import Sale


class SaleSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    revenue = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    cost = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    unit_cost = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Sale
        fields = ["id", "product", "product_name", "sold_on", "quantity", "unit_price",
                  "unit_cost", "revenue", "cost", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_product(self, product):
        if product.owner_id != self.context["request"].user.id:
            raise serializers.ValidationError("Choose one of your own products.")
        return product

    def validate_sold_on(self, value):
        from .models import today
        if value > today():
            raise serializers.ValidationError("A sale can't be dated in the future.")
        return value

    def validate(self, attrs):
        product = attrs.get("product") or (self.instance and self.instance.product)
        # Cost is snapshotted on create, or when the product is changed on edit.
        if self.instance is None or "product" in attrs:
            attrs["unit_cost"] = Product.objects.get(pk=product.pk).total_cost
        return attrs
