import csv
from datetime import timedelta
from decimal import Decimal

from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import Sale, today
from .reports import PERIODS, build_report, resolve_range
from .serializers import SaleSerializer

DEFAULT_DAYS = {"day": 28, "week": 28, "month": 365}  # weeks default to 4 whole 7-day blocks
MAX_BUCKETS = 400


def _plain(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


def _date(request, key):
    raw = request.query_params.get(key)
    if not raw:
        return None
    from datetime import date
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValidationError({key: "Use the format YYYY-MM-DD."})


class SaleViewSet(viewsets.ModelViewSet):
    serializer_class = SaleSerializer
    http_method_names = ["get", "post", "put", "delete", "head", "options"]

    def get_queryset(self):
        qs = Sale.objects.filter(owner=self.request.user).select_related("product")
        p = self.request.query_params
        if product := p.get("product"):
            qs = qs.filter(product_id=product)
        if (d := _date(self.request, "from")):
            qs = qs.filter(sold_on__gte=d)
        if (d := _date(self.request, "to")):
            qs = qs.filter(sold_on__lte=d)
        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


def _report_for(request):
    period = request.query_params.get("period", "day")
    if period not in PERIODS:
        raise ValidationError({"period": "Choose day, week or month."})
    end = _date(request, "to") or today()
    start = _date(request, "from") or end - timedelta(days=DEFAULT_DAYS[period] - 1)
    if start > end:
        raise ValidationError({"from": "Start date must be on or before the end date."})
    if (end - start).days > MAX_BUCKETS * {"day": 1, "week": 7, "month": 31}[period]:
        raise ValidationError({"from": "That range is too long for this period. Narrow the dates."})
    start, end = resolve_range(period, start, end)  # only months are widened (to whole months)
    sales = Sale.objects.filter(owner=request.user, sold_on__gte=start, sold_on__lte=end).select_related("product")
    return build_report(sales, period, start, end)


@api_view(["GET"])
def sales_report(request):
    return Response(_plain(_report_for(request)))


@api_view(["GET"])
def sales_report_csv(request):
    report = _report_for(request)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="sales-{report["period"]}ly-{report["start"]}-to-{report["end"]}.csv"'
        if report["period"] != "day" else
        f'attachment; filename="sales-daily-{report["start"]}-to-{report["end"]}.csv"'
    )
    response.write("﻿")  # so Excel reads the rupee/dash characters correctly
    w = csv.writer(response)
    w.writerow(["Period", "Orders", "Units", "Revenue", "Cost", "Profit"])
    for r in report["series"]:
        w.writerow([r["label"], r["orders"], r["units"], r["revenue"], r["cost"], r["profit"]])
    t = report["totals"]
    w.writerow(["Total", t["orders"], t["units"], t["revenue"], t["cost"], t["profit"]])
    return response
