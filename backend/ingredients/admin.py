from django.contrib import admin

from .models import Ingredient


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "quantity", "unit", "price", "active", "updated_at")
    list_editable = ("price", "active")  # quick price edits
    list_filter = ("owner", "unit", "active")
    search_fields = ("name",)
