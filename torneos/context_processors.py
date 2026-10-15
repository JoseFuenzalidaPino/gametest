from .views import es_administrador


def roles(request):
    user = request.user
    return {'es_admin': user.is_authenticated and es_administrador(user)}
