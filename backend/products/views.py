from decimal import Decimal

from django.db.models import ProtectedError
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Product
from .serializers import ProductSerializer


def _plain(value):
    """JSON-safe, exact money values (Decimal -> '55.00')."""
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    http_method_names = ["get", "post", "put", "delete", "head", "options"]  # full replace only

    def get_queryset(self):
        qs = Product.objects.filter(owner=self.request.user).prefetch_related("ingredients__ingredient")
        if search := self.request.query_params.get("search"):
            qs = qs.filter(name__icontains=search)
        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "This product has recorded sales, so it can't be deleted. Delete its sales first."},
                status=409,
            )

    @action(detail=False, methods=["post"])
    def calculate(self, request):
        """Preview the costing without saving anything."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        computed = serializer.validated_data["_computed"]
        return Response(_plain({
            "lines": [
                {
                    "ingredient": line["ingredient"].pk,
                    "ingredient_name": line["ingredient"].name,
                    "used_quantity": line["used_quantity"],
                    "used_unit": line["used_unit"],
                    "calculated_cost": line["calculated_cost"],
                }
                for line in computed["lines"]
            ],
            **{k: v for k, v in computed.items() if k != "lines"},
        }))
