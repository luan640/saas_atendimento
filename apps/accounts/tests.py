from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.cadastro.models import Loja
from .utils import get_shop_slug_from_host


class SubdomainTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(
            email="owner@example.com", password="123", is_owner=True
        )
        Loja.objects.create(owner=self.owner, nome="Loja1")

    def test_get_shop_slug_from_host(self):
        class DummyRequest:
            def __init__(self, host):
                self._host = host

            def get_host(self):
                return self._host

        req = DummyRequest("loja1.client.example.com")
        self.assertEqual(get_shop_slug_from_host(req), "loja1")

    def test_client_start_loja_subdomain(self):
        url = reverse("accounts:client_start_loja")
        response = self.client.get(url, HTTP_HOST="loja1.client.testserver")
        self.assertContains(response, "Identifique-se")

    def test_home_redirects_to_client_start(self):
        response = self.client.get('/', HTTP_HOST="loja1.client.testserver")
        self.assertRedirects(
            response,
            reverse("accounts:client_start_loja"),
            fetch_redirect_response=False,
        )
