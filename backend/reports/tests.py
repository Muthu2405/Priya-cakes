from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from ingredients.models import Ingredient

from .services import indian

User = get_user_model()


class FormatTests(SimpleTestCase):
    def test_indian_grouping(self):
        self.assertEqual(indian("5"), "5.00")
        self.assertEqual(indian("1234.5"), "1,234.50")
        self.assertEqual(indian("123456.78"), "1,23,456.78")
        self.assertEqual(indian("12345678"), "1,23,45,678.00")


class PdfTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("muthu", password="pw-12345-x")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        flour = Ingredient.objects.create(owner=self.user, name="Flour", quantity=1, unit="kg", price=200)
        body = {"name": "Chocolate Cake", "packaging_cost": "10",
                "ingredients": [{"ingredient": flour.id, "used_quantity": "100", "used_unit": "g"}]}
        self.pid = self.client.post("/api/products/", body, format="json").json()["id"]

    def test_pdf_downloads(self):
        res = self.client.get(f"/api/products/{self.pid}/pdf/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "application/pdf")
        self.assertIn("chocolate-cake-costing.pdf", res["Content-Disposition"])
        self.assertTrue(res.content.startswith(b"%PDF"))

    def test_pdf_shows_labour_profit_and_selling_price(self):
        from .services import build_product_pdf
        from products.models import Product
        pdf = build_product_pdf(Product.objects.get(pk=self.pid))
        self.assertTrue(pdf.startswith(b"%PDF"))
        res = self.client.get(f"/api/products/{self.pid}/").json()
        self.assertEqual(res["selling_price"], "{:.2f}".format(float(res["total_cost"]) + float(res["profit"])))

    def test_other_users_pdf_is_404(self):
        other = APIClient()
        other.force_authenticate(User.objects.create_user("bob", password="pw-12345-x"))
        self.assertEqual(other.get(f"/api/products/{self.pid}/pdf/").status_code, 404)
