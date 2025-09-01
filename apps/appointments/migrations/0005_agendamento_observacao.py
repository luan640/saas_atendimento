from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0004_agendamento_finalizacao"),
    ]

    operations = [
        migrations.AddField(
            model_name="agendamento",
            name="observacao",
            field=models.TextField(blank=True),
        ),
    ]
