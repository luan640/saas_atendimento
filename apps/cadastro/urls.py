from django.urls import path
from . import views
from apps.accounts.views import client_start_loja

app_name = 'cadastro'

urlpatterns = [
    path('lojas/', views.owner_shops, name='owner_shops'),
    path('funcionarios/', views.funcionarios, name='funcionarios'),
    path('servicos/', views.servicos, name='servicos'),
    path('<slug:slug>/', client_start_loja, name='client_start_loja'),
]