from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="agendamento",
            name="servico",
        ),
        migrations.AddField(
            model_name="agendamento",
            name="servicos",
            field=models.ManyToManyField(related_name="agendamentos", to="cadastro.servico"),
        ),
    ]
