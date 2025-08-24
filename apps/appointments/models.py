from django.db import models
from django.conf import settings

class Agendamento(models.Model):
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agendamentos"
    )
    loja = models.ForeignKey("cadastro.Loja", on_delete=models.CASCADE, related_name="agendamentos")
    funcionario = models.ForeignKey("cadastro.Funcionario", on_delete=models.CASCADE, related_name="agendamentos")
    servico = models.ForeignKey("cadastro.Servico", on_delete=models.CASCADE, related_name="agendamentos")

    data = models.DateField()
    hora = models.TimeField()

    criado_em = models.DateTimeField(auto_now_add=True)
    confirmado = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.cliente.full_name} – {self.servico.nome} ({self.data} {self.hora:%H:%M})"
