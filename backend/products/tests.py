from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from ingredients.models import Ingredient

from . import services

User = get_user_model()


def ing(name, qty, unit, price):
    return Ingredient(name=name, quantity=Decimal(qty), unit=unit, price=Decimal(price))


class CalculationTests(SimpleTestCase):
    def test_flour_100g_costs_20(self):
        flour = ing("Flour", "1", "kg", "200")
        self.assertEqual(services.ingredient_cost(flour, "100", "g"), Decimal("20.00"))

    def test_eggs_3_cost_18(self):
        egg = ing("Egg", "1", "pcs", "6")
        self.assertEqual(services.ingredient_cost(egg, "3", "pcs"), Decimal("18.00"))

    def test_butter_priced_per_500g(self):
        butter = ing("Butter", "500", "g", "250")
        self.assertEqual(services.ingredient_cost(butter, "100", "g"), Decimal("50.00"))

    def test_liters_to_ml(self):
        milk = ing("Milk", "1", "L", "70")
        self.assertEqual(services.ingredient_cost(milk, "250", "ml"), Decimal("17.50"))

    def test_incompatible_units_rejected(self):
        flour = ing("Flour", "1", "kg", "200")
        with self.assertRaises(services.IncompatibleUnitsError):
            services.ingredient_cost(flour, "1", "L")
        with self.assertRaises(services.IncompatibleUnitsError):
            services.ingredient_cost(flour, "3", "pcs")

    def test_full_product(self):
        lines = [
            {"ingredient": ing("Flour", "1", "kg", "200"), "used_quantity": Decimal("100"), "used_unit": "g"},
            {"ingredient": ing("Egg", "1", "pcs", "6"), "used_quantity": Decimal("3"), "used_unit": "pcs"},
        ]
        r = services.calculate_product(lines, "10", "5", "2")
        self.assertEqual(r["total_ingredient_cost"], Decimal("38.00"))
        self.assertEqual(r["total_additional_cost"], Decimal("17.00"))
        self.assertEqual(r["total_cost"], Decimal("55.00"))


class ApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("muthu", password="pw-12345-x")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.flour = Ingredient.objects.create(owner=self.user, name="Flour", quantity=1, unit="kg", price=200)
        self.egg = Ingredient.objects.create(owner=self.user, name="Egg", quantity=1, unit="pcs", price=6)

    def payload(self, **over):
        data = {
            "name": "Cake",
            "packaging_cost": "10", "eb_cost": "5", "labour_cost": "2",
            "ingredients": [
                {"ingredient": self.flour.id, "used_quantity": "100", "used_unit": "g"},
                {"ingredient": self.egg.id, "used_quantity": "3", "used_unit": "pcs"},
            ],
        }
        data.update(over)
        return data

    def test_create_and_snapshot_survives_price_change(self):
        res = self.client.post("/api/products/", self.payload(), format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()["total_cost"], "55.00")
        self.assertNotIn("cost_per_piece", res.json())

        self.flour.price = 220
        self.flour.save()
        detail = self.client.get(f"/api/products/{res.json()['id']}/").json()
        self.assertEqual(detail["total_cost"], "55.00")
        self.assertEqual(detail["ingredients"][0]["calculated_cost"], "20.00")

    def test_profit_defaults_to_30_percent_of_cost(self):
        res = self.client.post("/api/products/", self.payload(), format="json").json()
        self.assertEqual(res["total_cost"], "55.00")
        self.assertEqual(res["profit"], "16.50")         # 30% of 55
        self.assertEqual(res["selling_price"], "71.50")
        self.assertEqual(res["labour_cost"], "2.00")
        self.assertNotIn("other_cost", res)

    def test_profit_can_be_overridden_including_zero(self):
        res = self.client.post("/api/products/", self.payload(profit="25"), format="json").json()
        self.assertEqual((res["profit"], res["selling_price"]), ("25.00", "80.00"))
        res = self.client.post("/api/products/", self.payload(profit="0"), format="json").json()
        self.assertEqual((res["profit"], res["selling_price"]), ("0.00", "55.00"))
        bad = self.client.post("/api/products/", self.payload(profit="-1"), format="json")
        self.assertEqual(bad.status_code, 400)

    def test_calculate_suggests_default_profit_even_when_overridden(self):
        res = self.client.post("/api/products/calculate/", self.payload(profit="10"), format="json").json()
        self.assertEqual((res["default_profit"], res["profit"], res["selling_price"]), ("16.50", "10.00", "65.00"))

    def test_update_replaces_lines_and_recalculates(self):
        pid = self.client.post("/api/products/", self.payload(), format="json").json()["id"]
        body = self.payload(packaging_cost="20", ingredients=[
            {"ingredient": self.egg.id, "used_quantity": "2", "used_unit": "pcs"}])
        res = self.client.put(f"/api/products/{pid}/", body, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["total_cost"], "39.00")  # 12 + 20 + 5 + 2
        self.assertEqual(len(res.json()["ingredients"]), 1)

    def test_calculate_does_not_save(self):
        res = self.client.post("/api/products/calculate/", self.payload(), format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["total_cost"], "55.00")
        self.assertEqual(len(self.client.get("/api/products/").json()), 0)

    def test_validation(self):
        bad = [
            self.payload(ingredients=[]),
            self.payload(packaging_cost="-1"),
            self.payload(name="  "),
            self.payload(ingredients=[{"ingredient": self.flour.id, "used_quantity": "-5", "used_unit": "g"}]),
            self.payload(ingredients=[{"ingredient": self.flour.id, "used_quantity": "NaN", "used_unit": "g"}]),
            self.payload(ingredients=[{"ingredient": self.flour.id, "used_quantity": "1", "used_unit": "L"}]),
        ]
        for payload in bad:
            res = self.client.post("/api/products/", payload, format="json")
            self.assertEqual(res.status_code, 400, payload)

    def test_delete_used_ingredient_deactivates(self):
        self.client.post("/api/products/", self.payload(), format="json")
        res = self.client.delete(f"/api/ingredients/{self.flour.id}/")
        self.assertEqual(res.status_code, 200)
        self.flour.refresh_from_db()
        self.assertFalse(self.flour.active)

    def test_ingredient_validation_and_search(self):
        for bad in ({"quantity": "0"}, {"price": "-5"}, {"name": "  "}):
            body = {"name": "X", "quantity": "1", "unit": "kg", "price": "5", **bad}
            self.assertEqual(self.client.post("/api/ingredients/", body, format="json").status_code, 400, bad)
        res = self.client.get("/api/ingredients/?search=flo")
        self.assertEqual([i["name"] for i in res.json()], ["Flour"])

    def test_new_ingredient_belongs_to_creator(self):
        res = self.client.post("/api/ingredients/", {"name": "Sugar", "quantity": "1", "unit": "kg", "price": "80"}, format="json")
        self.assertEqual(Ingredient.objects.get(pk=res.json()["id"]).owner, self.user)


class IsolationTests(TestCase):
    """Each user only ever sees and uses their own data."""

    def setUp(self):
        self.alice = User.objects.create_user("alice", password="pw-12345-x")
        self.bob = User.objects.create_user("bob", password="pw-12345-x")
        self.a = APIClient(); self.a.force_authenticate(self.alice)
        self.b = APIClient(); self.b.force_authenticate(self.bob)
        self.flour = Ingredient.objects.create(owner=self.alice, name="Flour", quantity=1, unit="kg", price=200)
        body = {"name": "Cake", "ingredients": [{"ingredient": self.flour.id, "used_quantity": "100", "used_unit": "g"}]}
        self.product_id = self.a.post("/api/products/", body, format="json").json()["id"]

    def test_lists_are_separate(self):
        self.assertEqual(len(self.a.get("/api/ingredients/").json()), 1)
        self.assertEqual(self.b.get("/api/ingredients/").json(), [])
        self.assertEqual(self.b.get("/api/products/").json(), [])

    def test_other_users_records_are_404(self):
        self.assertEqual(self.b.get(f"/api/products/{self.product_id}/").status_code, 404)
        self.assertEqual(self.b.delete(f"/api/products/{self.product_id}/").status_code, 404)
        self.assertEqual(self.b.get(f"/api/ingredients/{self.flour.id}/").status_code, 404)
        self.assertEqual(self.b.put(f"/api/ingredients/{self.flour.id}/", {"name": "x", "quantity": "1", "unit": "kg", "price": "1"}, format="json").status_code, 404)

    def test_cannot_use_someone_elses_ingredient(self):
        body = {"name": "Mine", "ingredients": [{"ingredient": self.flour.id, "used_quantity": "100", "used_unit": "g"}]}
        self.assertEqual(self.b.post("/api/products/", body, format="json").status_code, 400)
        self.assertEqual(self.b.post("/api/products/calculate/", body, format="json").status_code, 400)
