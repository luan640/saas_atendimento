from django.urls import path
from . import views
from apps.accounts.views import client_start_loja

app_name = 'cadastro'

urlpatterns = [
    
    # ======= LOJAS ========
    path('lojas/', views.owner_shops, name='owner_shops'),
    path('lojas/<int:pk>/edit/', views.owner_shop_edit, name='owner_shop_edit'),
    path('lojas/<int:pk>/delete/', views.owner_shop_delete, name='owner_shop_delete'),

    path('funcionarios/', views.funcionarios, name='funcionarios'),
    path('servicos/form/', views.servico_form, name='servico_form'),
    path('servicos/', views.servicos, name='servicos'),
    path('<slug:slug>/', client_start_loja, name='client_start_loja'),
]