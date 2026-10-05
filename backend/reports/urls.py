from django.urls import path

from .views import product_pdf

urlpatterns = [
    path("products/<int:pk>/pdf/", product_pdf),
]
