from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import SaleViewSet, sales_report, sales_report_csv

router = DefaultRouter()
router.register("sales", SaleViewSet, basename="sale")

# Report routes first so "report" is never read as a sale id.
urlpatterns = [
    path("sales/report/", sales_report),
    path("sales/report/csv/", sales_report_csv),
] + router.urls
