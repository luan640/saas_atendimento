from django.urls import path
from . import views

app_name = "appointments"

urlpatterns = [
    path("agendar/", views.agendamento_start, name="agendamento_start"),
    path("agendar/<int:funcionario_id>/servicos/", views.agendamento_servicos, name="agendamento_servicos"),
    path("agendar/<int:funcionario_id>/servico/<int:servico_id>/horario/", views.agendamento_datahora, name="agendamento_datahora"),
    path("agendar/<int:agendamento_id>/confirmacao/", views.agendamento_confirmacao, name="agendamento_confirmacao"),
]
