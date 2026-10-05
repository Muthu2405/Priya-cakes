from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from ingredients.models import Ingredient

User = get_user_model()


class AuthTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("muthu", password="pw-12345-x")
        self.client = APIClient()

    def login(self, password="pw-12345-x"):
        return self.client.post("/api/auth/login/", {"username": "muthu", "password": password}, format="json")

    def test_login_returns_token_that_works(self):
        res = self.login()
        self.assertEqual(res.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {res.json()['token']}")
        self.assertEqual(self.client.get("/api/auth/me/").json(), {"username": "muthu"})

    def test_wrong_password_rejected(self):
        res = self.login("nope")
        self.assertEqual(res.status_code, 400)
        self.assertNotIn("token", res.json())

    def test_api_requires_login(self):
        for url in ("/api/ingredients/", "/api/products/", "/api/auth/me/", "/api/products/1/pdf/"):
            self.assertEqual(self.client.get(url).status_code, 401, url)

    def test_logout_invalidates_token(self):
        token = self.login().json()["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(self.client.post("/api/auth/logout/").status_code, 204)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    def test_claim_orphans(self):
        Ingredient.objects.create(name="Old", quantity=1, unit="kg", price=10)
        call_command("claim_orphans", "muthu")
        self.assertEqual(Ingredient.objects.get(name="Old").owner, self.user)
