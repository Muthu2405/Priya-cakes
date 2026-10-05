from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("ingredients.urls")),
    path("api/", include("products.urls")),
    path("api/", include("sales.urls")),
    path("api/", include("reports.urls")),
]
