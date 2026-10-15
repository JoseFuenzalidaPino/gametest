from rest_framework.permissions import SAFE_METHODS, BasePermission

from .roles import es_administrador


class EsAdministradorOSoloLectura(BasePermission):
    """Lectura para usuarios autenticados; escritura solo para administradores."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or es_administrador(user)
