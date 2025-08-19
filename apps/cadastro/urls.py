from django.urls import path
from . import views
from apps.accounts.views import client_start_loja

app_name = 'cadastro'

urlpatterns = [
    path('owner/lojas/', views.owner_shops, name='owner_shops'),
    path('owner/lojas/<int:pk>/editar/', views.owner_shop_edit, name='owner_shop_edit'),
    path('owner/lojas/<int:pk>/excluir/', views.owner_shop_delete, name='owner_shop_delete'),
    path('owner/lojas/<int:loja_id>/funcionarios/', views.owner_staff, name='owner_staff'),
    path('owner/lojas/<int:loja_id>/funcionarios/<int:pk>/editar/', views.owner_staff_edit, name='owner_staff_edit'),
    path('owner/lojas/<int:loja_id>/funcionarios/<int:pk>/excluir/', views.owner_staff_delete, name='owner_staff_delete'),
    path('owner/lojas/<int:loja_id>/servicos/', views.owner_services, name='owner_services'),
    path('owner/lojas/<int:loja_id>/servicos/<int:pk>/editar/', views.owner_service_edit, name='owner_service_edit'),
    path('owner/lojas/<int:loja_id>/servicos/<int:pk>/excluir/', views.owner_service_delete, name='owner_service_delete'),
    path('<slug:slug>/', client_start_loja, name='client_start_loja'),
]
