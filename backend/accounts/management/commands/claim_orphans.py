from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from ingredients.models import Ingredient
from products.models import Product


class Command(BaseCommand):
    help = "Assign ingredients and products that have no owner (created before login existed) to a user."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist:
            raise CommandError(f"No user named {options['username']!r}.")
        ingredients = Ingredient.objects.filter(owner__isnull=True).update(owner=user)
        products = Product.objects.filter(owner__isnull=True).update(owner=user)
        self.stdout.write(f"Assigned {ingredients} ingredients and {products} products to {user}.")
