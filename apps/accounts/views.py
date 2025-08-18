import random
from datetime import timedelta
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse

from .forms import OwnerLoginForm, ClientStartForm, ClientVerifyForm
from .models import User, ClientOTP, Subscription, Plan

# ========== OWNER ==========

def owner_login(request):
    if request.method == 'POST':
        form = OwnerLoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            # garante assinatura
            sub = getattr(user, 'subscription', None)
            if not sub:
                # cria trial de 7 dias
                sub = Subscription.objects.create(
                    owner=user,
                    plan=Plan.FREE,
                    start_date=timezone.now(),
                    end_date=timezone.now() + timedelta(days=7)
                )
            login(request, user)
            return redirect('accounts:owner_dashboard')
    else:
        form = OwnerLoginForm()
    return render(request, 'accounts/owner_login.html', {'form': form})

@login_required
def owner_dashboard(request):
    user = request.user
    sub = getattr(user, 'subscription', None)
    return render(request, 'accounts/owner_dashboard.html', {'subscription': sub})

@login_required
def owner_logout(request):
    logout(request)
    return redirect('accounts:owner_login')

# ========== CLIENTE (OTP por telefone) ==========

def client_start(request):
    # Coleta nome + telefone e gera código
    if request.method == 'POST':
        form = ClientStartForm(request.POST)
        if form.is_valid():
            full_name = form.cleaned_data['full_name']
            phone = form.cleaned_data['phone']
            code = f"{random.randint(0, 999999):06d}"
            otp = ClientOTP.objects.create(
                phone=phone,
                code=code,
                created_at=timezone.now(),
                expires_at=timezone.now() + timedelta(minutes=5),
            )
            # Em produção: enviar via SMS/WhatsApp. Aqui: console + mensagem
            print(f"[DEBUG OTP] Enviar {code} para {phone}")
            messages.success(request, "Código de verificação enviado (ver console de servidor).")
            form_verify = ClientVerifyForm(initial={'phone': phone})
            return redirect(f"{reverse('accounts:client_verify')}?phone={phone}")
    else:
        form = ClientStartForm()
    return render(request, 'accounts/client_start.html', {'form': form})


def client_verify(request):
    phone = request.GET.get('phone') or request.POST.get('phone')
    if request.method == 'POST':
        form = ClientVerifyForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data['phone']
            code = form.cleaned_data['code']
            otp = ClientOTP.objects.filter(phone=phone).order_by('-created_at').first()
            if not otp or not otp.is_valid() or otp.code != code:
                messages.error(request, 'Código inválido ou expirado.')
            else:
                # cria/pega usuário cliente
                user, _ = User.objects.get_or_create(
                    phone=phone,
                    defaults={
                        'email': f"cliente-{phone}@example.local",
                        'is_client': True,
                        'is_owner': False,
                        'full_name': request.POST.get('full_name') or 'Cliente',
                    }
                )
                # garante marcador de cliente
                if not user.is_client:
                    user.is_client = True
                    user.save(update_fields=['is_client'])
                login(request, user)
                return redirect('accounts:client_dashboard')
    else:
        form = ClientVerifyForm(initial={'phone': phone})
    return render(request, 'accounts/client_verify.html', {'form': form, 'phone': phone})

@login_required
def client_dashboard(request):
    return render(request, 'accounts/client_dashboard.html', {})