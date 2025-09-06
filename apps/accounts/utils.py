from typing import Optional

from django.http import HttpRequest

def get_shop_slug_from_host(request: HttpRequest) -> Optional[str]:
    """Extract shop slug from host like <shop>.client.<domain>."""
    host = request.get_host().split(':')[0]
    parts = host.split('.')

    print(host, parts)

    if len(parts) >= 3 and parts[1] == 'client':
        return parts[0]
    return None
