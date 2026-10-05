from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import Ingredient
from .serializers import IngredientSerializer


class IngredientViewSet(viewsets.ModelViewSet):
    """CRUD for the ingredient price database.

    Supports ?search=<name>, ?unit=<kg|g|L|ml|pcs> and ?active=<true|false>.
    DELETE removes an unused ingredient, but only deactivates one that is
    already used in saved products (so historical costings stay intact).
    """

    serializer_class = IngredientSerializer

    def get_queryset(self):
        qs = Ingredient.objects.filter(owner=self.request.user)
        p = self.request.query_params
        if search := p.get("search"):
            qs = qs.filter(name__icontains=search)
        if unit := p.get("unit"):
            qs = qs.filter(unit=unit)
        if (active := p.get("active")) is not None:
            qs = qs.filter(active=active.lower() in ("1", "true", "yes"))
        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def destroy(self, request, *args, **kwargs):
        ingredient = self.get_object()
        if ingredient.product_lines.exists():
            ingredient.active = False
            ingredient.save(update_fields=["active", "updated_at"])
            return Response(
                {"detail": "Ingredient is used in saved products, so it was deactivated instead of deleted."},
                status=status.HTTP_200_OK,
            )
        return super().destroy(request, *args, **kwargs)
