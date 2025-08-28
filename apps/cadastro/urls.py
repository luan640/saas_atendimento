from django.urls import path
from . import views
from apps.accounts.views import client_start_loja

app_name = 'cadastro'

urlpatterns = [
    
    # ======= LOJAS ========
    path('lojas/', views.owner_shops, name='owner_shops'),
    path('lojas/<int:pk>/edit/', views.owner_shop_edit, name='owner_shop_edit'),
    path('lojas/<int:pk>/delete/', views.owner_shop_delete, name='owner_shop_delete'),

    # ======== FUNCIONARIOS ========
    path('funcionarios/', views.funcionarios, name='funcionarios'),
    path('funcionarios/<int:pk>/edit/', views.funcionario_edit, name='funcionario_edit'),
    path('funcionarios/<int:pk>/delete/', views.funcionario_delete, name='funcionario_delete'),

    # ======== SERVIÇOS ========
    path('servicos/form/', views.servico_form, name='servico_form'),
    path('servicos/', views.servicos, name='servicos'),
    path('servicos/<int:pk>/edit/', views.servico_edit, name='servico_edit'),
    path('servicos/<int:pk>/delete/', views.servico_delete, name='servico_delete'),

    path('<slug:slug>/', client_start_loja, name='client_start_loja'),
]