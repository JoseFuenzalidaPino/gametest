from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def es_administrador(user):
    return user.is_staff or user.groups.filter(name="Administrador").exists()


def admin_requerido(vista):
    """Exige sesión iniciada (redirige al login) y rol Administrador (si no, error 403)."""
    @wraps(vista)
    @login_required
    def envoltura(request, *args, **kwargs):
        if not es_administrador(request.user):
            raise PermissionDenied
        return vista(request, *args, **kwargs)
    return envoltura
