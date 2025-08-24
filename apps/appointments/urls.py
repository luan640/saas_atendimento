from django.urls import path
from . import views

app_name = "appointments"

urlpatterns = [
    path("agendar/", views.agendamento_start, name="agendamento_start"),
    path("agendar/profissionais/", views.agendamento_profissionais, name="agendamento_profissionais"),
    path("agendar/<int:funcionario_id>/servicos/", views.agendamento_servicos, name="agendamento_servicos"),
    path("agendar/datahora/", views.agendamento_datahora, name="agendamento_datahora"),
    path("agendar/confirmacao/<int:agendamento_id>/", views.agendamento_confirmacao, name="agendamento_confirmacao"),
]
