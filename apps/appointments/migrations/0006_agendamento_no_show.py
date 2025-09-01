from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0005_agendamento_observacao"),
    ]

    operations = [
        migrations.AddField(
            model_name="agendamento",
            name="no_show",
            field=models.BooleanField(default=False),
        ),
    ]
