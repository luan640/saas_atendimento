# utils/hosts.py
from typing import Optional
from django.http import HttpRequest
from django.utils.text import slugify

def get_shop_slug_from_host(request: HttpRequest) -> Optional[str]:
    """
    Aceita:
      - <shop>.<owner_first_name>.<domínio>
      - <shop>.client.<domínio>   (compat)
    Em dev: ... .localhost:8000
    """
    host = request.get_host().split(':')[0]
    parts = host.split('.')

    # IPv4 ou poucos labels -> não há subdomínio utilizável
    is_ipv4 = (len(parts) == 4 and all(p.isdigit() for p in parts))
    if is_ipv4 or len(parts) < 3:
        return None

    shop, second = parts[0], parts[1]

    # compat: <shop>.client.<domínio>
    if second == 'client':
        return shop

    # formato novo: validar segundo label contra first_name do owner
    from apps.cadastro.models import Loja  # ajuste o import conforme seu projeto
    loja = (Loja.objects
            .select_related('owner')
            .filter(slug=shop, ativa=True)
            .first())
    if not loja:
        return None

    expected = slugify(loja.owner.first_name or '') or 'owner'
    return shop if second == expected else None
