from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Owner
    path('login/', views.owner_login, name='owner_login'),
    path('logout/', views.owner_logout, name='owner_logout'),
    path('dashboard/', views.owner_dashboard, name='owner_dashboard'),

    # Cliente (OTP)
    path('client/start/', views.client_start, name='client_start'),
    path('client/verify/', views.client_verify, name='client_verify'),
    path('client/dashboard/', views.client_dashboard, name='client_dashboard'),
]