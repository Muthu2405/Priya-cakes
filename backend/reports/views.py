from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from rest_framework.decorators import api_view

from products.models import Product

from .services import build_product_pdf


@api_view(["GET"])
def product_pdf(request, pk):
    product = get_object_or_404(
        Product.objects.filter(owner=request.user).prefetch_related("ingredients__ingredient"), pk=pk
    )
    filename = f"{slugify(product.name) or 'product'}-costing.pdf"
    response = HttpResponse(build_product_pdf(product), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
