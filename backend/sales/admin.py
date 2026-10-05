from django.contrib import admin

from .models import Sale


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("product_name", "owner", "sold_on", "quantity", "unit_price", "unit_cost")
    list_filter = ("owner", "sold_on")
