from django.contrib import admin

from .models import Product, ProductIngredient


class ProductIngredientInline(admin.TabularInline):
    model = ProductIngredient
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "total_cost", "created_at")
    list_filter = ("owner",)
    search_fields = ("name",)
    inlines = [ProductIngredientInline]


admin.site.register(ProductIngredient)
