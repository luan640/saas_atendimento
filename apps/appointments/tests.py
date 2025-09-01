from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.cadastro.models import (
    Loja,
    LojaAgendamentoConfig,
    Funcionario,
    FuncionarioAgendaSemanal,
    Servico,
)
from .utils import gerar_slots_disponiveis


class SlotDisponivelTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(
            email="owner@example.com", password="123", is_owner=True
        )
        self.loja = Loja.objects.create(owner=self.owner, nome="Loja Teste")
        LojaAgendamentoConfig.objects.create(loja=self.loja, slot_interval_minutes=30)
        self.funcionario = Funcionario.objects.create(loja=self.loja, nome="Bob")
        FuncionarioAgendaSemanal.objects.create(
            funcionario=self.funcionario,
            weekday=0,
            inicio=time(9, 0),
            fim=time(10, 0),
            slot_interval_minutes=30,
        )
        self.servico = Servico.objects.create(
            loja=self.loja, nome="Corte", duracao_minutos=30, preco=10
        )
        self.servico.profissionais.add(self.funcionario)

    def test_gerar_slots_sem_agendamentos(self):
        slots = gerar_slots_disponiveis(self.funcionario, date(2024, 1, 1), 30)
        horas = [s.time() for s in slots]
        self.assertEqual(horas, [time(9, 0), time(9, 30)])

    def test_gerar_slots_com_agendamento_existente(self):
        # cria agendamento às 9:00
        ag = self.funcionario.agendamentos.create(
            cliente=self.owner,
            loja=self.loja,
            data=date(2024, 1, 1),
            hora=time(9, 0),
        )
        ag.servicos.add(self.servico)
        slots = gerar_slots_disponiveis(self.funcionario, date(2024, 1, 1), 30)
        horas = [s.time() for s in slots]
        self.assertEqual(horas, [time(9, 30)])
