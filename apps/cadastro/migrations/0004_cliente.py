from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cadastro', '0003_lojaagendamentoconfig_funcionarioagendaexcecao_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Cliente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('owner', models.ForeignKey(limit_choices_to={'is_owner': True}, on_delete=django.db.models.deletion.CASCADE, related_name='clientes', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(limit_choices_to={'is_client': True}, on_delete=django.db.models.deletion.CASCADE, related_name='cliente_de', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('user__full_name',),
                'unique_together': {('owner', 'user')},
            },
        ),
    ]
