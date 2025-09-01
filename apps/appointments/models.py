from django.db import models
from django.conf import settings
from django.db.models import Sum
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

class Agendamento(models.Model):
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agendamentos"
    )
    loja = models.ForeignKey("cadastro.Loja", on_delete=models.CASCADE, related_name="agendamentos")
    funcionario = models.ForeignKey("cadastro.Funcionario", on_delete=models.CASCADE, related_name="agendamentos")
    servicos = models.ManyToManyField("cadastro.Servico", related_name="agendamentos")

    duracao_total_minutos = models.PositiveIntegerField(default=0)

    data = models.DateField()
    hora = models.TimeField()

    criado_em = models.DateTimeField(auto_now_add=True)
    confirmado = models.BooleanField(default=False)

    class FormaPagamento(models.TextChoices):
        PIX = "pix", "PIX"
        DEBITO = "debito", "Débito"
        DINHEIRO = "dinheiro", "Dinheiro"
        CREDITO = "credito", "Cartão de Crédito"

    valor_final = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    teve_desconto = models.BooleanField(default=False)
    forma_pagamento = models.CharField(
        max_length=20, choices=FormaPagamento.choices, blank=True, null=True
    )
    finalizado_em = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        nomes = ", ".join(s.nome for s in self.servicos.all()[:3])
        if self.servicos.count() > 3:
            nomes += "..."
        return f"{self.cliente.full_name} – {nomes} ({self.data} {self.hora:%H:%M})"


@receiver(m2m_changed, sender=Agendamento.servicos.through)
def atualizar_duracao_total(sender, instance: Agendamento, action, **kwargs):
    """Atualiza ``duracao_total_minutos`` ao alterar os serviços do agendamento."""
    if action in {"post_add", "post_remove", "post_clear"}:
        total = instance.servicos.aggregate(total=Sum("duracao_minutos"))
        instance.duracao_total_minutos = total["total"] or 0
        instance.save(update_fields=["duracao_total_minutos"])
