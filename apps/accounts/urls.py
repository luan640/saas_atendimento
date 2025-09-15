from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.home_redirect, name='home'),
    # Owner
    path('login/', views.owner_login, name='owner_login'),
    path('logout/', views.owner_logout, name='owner_logout'),
    path('home/', views.owner_home, name='owner_home'),
    path('home/dashboard/', views.owner_dashboard, name='owner_dashboard'),
    path('home/historico/', views.owner_historico, name='owner_historico'),
    path("home/agendamentos/", views.owner_home_agendamentos, name="owner_home_agendamentos"),
    path("home/criar-atendimento/", views.owner_criar_atendimento, name="owner_criar_atendimento"),
    path("home/criar-atendimento/add-cliente/", views.owner_add_cliente, name="owner_add_cliente"),
    path("home/criar-atendimento/slots/", views.owner_slots_disponiveis, name="owner_slots_disponiveis"),
    path('home/fields-by-loja/', views.owner_fields_by_loja, name='owner_fields_by_loja'),

    path("sobre/", views.owner_sobre, name="owner_sobre"),

    # Cliente (OTP)
    path('', views.client_start_loja, name='client_start_loja'),
    path('client/verify/', views.client_verify, name='client_verify'),
    path('client/dashboard/', views.client_dashboard, name='client_dashboard'),
    path('client/resend/', views.client_resend_code, name='client_resend_code'),

]
