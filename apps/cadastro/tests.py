from datetime import time

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Loja, Funcionario
from .views import _agenda_formset


class AgendaSemanalFormsetTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(
            email="owner@example.com", password="123", is_owner=True
        )
        self.loja = Loja.objects.create(owner=self.owner, nome="Loja Teste")

    def test_salva_apenas_dias_preenchidos(self):
        """Formset deve salvar somente os dias que possuem horários"""
        func_inst = Funcionario(loja=self.loja, nome="Temp")
        data = {
            "agenda-TOTAL_FORMS": "7",
            "agenda-INITIAL_FORMS": "0",
            "agenda-MIN_NUM_FORMS": "0",
            "agenda-MAX_NUM_FORMS": "7",
        }
        for i in range(7):
            data[f"agenda-{i}-weekday"] = str(i)
        data.update(
            {
                "agenda-0-inicio": "09:00",
                "agenda-0-fim": "18:00",
                "agenda-0-ativo": "on",
            }
        )

        formset = _agenda_formset(func_inst, data)
        self.assertTrue(formset.is_valid())

        func = Funcionario.objects.create(loja=self.loja, nome="Bob")
        formset.instance = func
        formset.save()

        ags = func.agendas_semanais.all()
        self.assertEqual(ags.count(), 1)
        ag = ags.first()
        self.assertEqual(ag.weekday, 0)
        self.assertEqual(ag.inicio, time(9, 0))
        self.assertEqual(ag.fim, time(18, 0))
