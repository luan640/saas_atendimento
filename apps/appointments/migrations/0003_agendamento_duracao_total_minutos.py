from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0002_agendamento_servicos"),
    ]

    operations = [
        migrations.AddField(
            model_name="agendamento",
            name="duracao_total_minutos",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
