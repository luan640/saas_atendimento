from django.shortcuts import redirect
from django.urls import reverse


class LoginRequiredMiddleware:
    """Redireciona visitantes não autenticados para a tela de login."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        allowed = (
            reverse('accounts:owner_login'),
            reverse('accounts:owner_logout'),
            reverse('accounts:client_start_loja'),
            reverse('accounts:client_verify'),
        )
        if (
            not request.user.is_authenticated
            and path not in allowed
            and not path.startswith('/static/')
            and not path.startswith('/admin/')
        ):
            return redirect('accounts:owner_login')
        return self.get_response(request)


class SubscriptionRequiredMiddleware:
    """Restringe páginas do Owner quando a assinatura estiver expirada."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        # URLs liberadas (login, logout, cliente)
        allowed = (
            reverse('accounts:owner_login'),
            reverse('accounts:owner_logout'),
            reverse('accounts:client_start_loja'),
            reverse('accounts:client_verify'),
        )
        if request.user.is_authenticated and getattr(request.user, 'is_owner', False):
            # evita loop
            if path not in allowed:
                sub = getattr(request.user, 'subscription', None)
                if not sub or not sub.is_active():
                    return redirect('accounts:owner_login')
        return self.get_response(request)
