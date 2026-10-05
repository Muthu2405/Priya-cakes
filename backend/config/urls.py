from django.conf import settings
from django.contrib import admin
from django.http import Http404, HttpResponse
from django.urls import include, path, re_path


def spa(request, *args, **kwargs):
    """Serve the React app for any page route, so a refresh on /sales/report still works."""
    index = settings.FRONTEND_DIST / "index.html"
    if not index.is_file():
        raise Http404
    return HttpResponse(index.read_text(encoding="utf-8"), content_type="text/html")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("ingredients.urls")),
    path("api/", include("products.urls")),
    path("api/", include("sales.urls")),
    path("api/", include("reports.urls")),
    re_path(r"^(?!api/|admin/|static/).*$", spa),
]
