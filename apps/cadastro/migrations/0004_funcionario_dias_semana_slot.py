from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cadastro", "0003_lojaagendamentoconfig_funcionarioagendaexcecao_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="funcionario",
            name="dias_semana",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Dias da semana que o funcionário atende (0=Segunda ... 6=Domingo), separados por vírgula",
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name="funcionario",
            name="slot_interval_minutes",
            field=models.PositiveSmallIntegerField(
                default=30,
                help_text="Duração padrão de cada slot de atendimento em minutos",
            ),
        ),
    ]
