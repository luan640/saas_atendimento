from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.owner_login, name='home'),
    # Owner
    path('login/', views.owner_login, name='owner_login'),
    path('logout/', views.owner_logout, name='owner_logout'),
    path('home/', views.owner_home, name='owner_home'),
    path("home/agendamentos/", views.owner_home_agendamentos, name="owner_home_agendamentos"),
    path("home/criar-atendimento/", views.owner_criar_atendimento, name="owner_criar_atendimento"),
    path("sobre/", views.owner_sobre, name="owner_sobre"),

    # Cliente (OTP)
    path('client/start/<slug:slug>/', views.client_start_loja, name='client_start_loja'),
    path('client/verify/', views.client_verify, name='client_verify'),
    path('client/dashboard/', views.client_dashboard, name='client_dashboard'),
]