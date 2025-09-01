from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0003_agendamento_duracao_total_minutos"),
    ]

    operations = [
        migrations.AddField(
            model_name="agendamento",
            name="valor_final",
            field=models.DecimalField(blank=True, null=True, max_digits=10, decimal_places=2),
        ),
        migrations.AddField(
            model_name="agendamento",
            name="teve_desconto",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="agendamento",
            name="forma_pagamento",
            field=models.CharField(
                choices=[
                    ("pix", "PIX"),
                    ("debito", "Débito"),
                    ("dinheiro", "Dinheiro"),
                    ("credito", "Cartão de Crédito"),
                ],
                max_length=20,
                blank=True,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="agendamento",
            name="finalizado_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
