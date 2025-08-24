from functools import wraps
from django.shortcuts import redirect

def subscription_required(view_func):
    """
    Garante que o owner tenha uma assinatura ativa antes de acessar a view.
    Se não tiver, redireciona para o login do owner.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if (
            request.user.is_authenticated
            and getattr(request.user, "is_owner", False)
        ):
            sub = getattr(request.user, "subscription", None)
            if not sub or not sub.is_active():
                return redirect("accounts:owner_login")
        return view_func(request, *args, **kwargs)
    return _wrapped
