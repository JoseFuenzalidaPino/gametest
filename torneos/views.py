from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group
from django.db.models import Count
from django.utils.http import url_has_allowed_host_and_scheme
from rest_framework import viewsets
from .models import Torneo, Inscripcion, Jugador
from .forms import TorneoForm, LoginForm, RegistroForm
from .serializers import TorneoSerializer


def es_administrador(user):
    return user.is_staff or user.groups.filter(name="Administrador").exists()


def obtener_jugador(user):
    jugador, _ = Jugador.objects.get_or_create(user=user, defaults={"nickname": user.username})
    return jugador


@login_required
def inscribirse_torneo(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    jugador = obtener_jugador(request.user)

    if Inscripcion.objects.filter(torneo=torneo, jugador=jugador).exists():
        return render(request, 'torneos/mensaje.html', {'mensaje': 'Ya estás inscrito en este torneo.'})

    if torneo.estado != 'DISPONIBLE':
        return render(request, 'torneos/mensaje.html', {'mensaje': 'Este torneo no admite inscripciones.'})

    inscripciones_actuales = Inscripcion.objects.filter(torneo=torneo).count()
    if inscripciones_actuales >= torneo.max_participantes:
        return render(request, 'torneos/mensaje.html', {'mensaje': 'No hay cupos disponibles.'})

    Inscripcion.objects.create(torneo=torneo, jugador=jugador)
    return render(request, 'torneos/mensaje.html', {'mensaje': 'Inscripción exitosa.'})


def redirigir_a_panel(user):
    if es_administrador(user):
        return redirect("admin_panel")   # si es admin, va a su panel
    return redirect("jugador_panel")     # si es jugador, va a su panel

def registrar_usuario(request):
    if request.user.is_authenticated:
        return redirigir_a_panel(request.user)
    form = RegistroForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        grupo_jugador, _ = Group.objects.get_or_create(name="Usuarios")  # asigna rol Jugador
        user.groups.add(grupo_jugador)
        obtener_jugador(user)
        messages.success(request, "Cuenta creada, ya puedes iniciar sesión")
        return redirect("login")
    return render(request, "usuarios/registro.html", {"form": form})

def iniciar_sesion(request):
    if request.user.is_authenticated:
        return redirigir_a_panel(request.user)
    form = LoginForm(request, data=request.POST or None)
    siguiente = request.POST.get("next") or request.GET.get("next", "")
    if form.is_valid():
        login(request, form.get_user())
        if url_has_allowed_host_and_scheme(siguiente, allowed_hosts={request.get_host()}):
            return redirect(siguiente)
        return redirigir_a_panel(form.get_user())
    return render(request, "usuarios/login.html", {"form": form, "next": siguiente})

def cerrar_sesion(request):
    logout(request)
    return redirect("login")

@login_required
def jugador_panel(request):
    inscripciones = (Inscripcion.objects.filter(jugador__user=request.user)
                     .select_related('torneo').order_by('torneo__fecha'))
    return render(request, "usuarios/jugador_panel.html", {"inscripciones": inscripciones})

@login_required
@user_passes_test(es_administrador)
def admin_panel(request):
    torneos = Torneo.objects.annotate(inscritos=Count('inscripcion')).order_by('-fecha')
    return render(request, "usuarios/admin_panel.html", {
        "torneos": torneos,
        "total_jugadores": Jugador.objects.count(),
        "total_inscripciones": Inscripcion.objects.count(),
    })

class TorneoViewSet(viewsets.ModelViewSet):
    queryset = Torneo.objects.all()
    serializer_class = TorneoSerializer

def lista_torneos(request):
    torneos = Torneo.objects.all()
    return render(request, 'torneos/lista.html', {'torneos': torneos})

def crear_torneo(request):
    form = TorneoForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('lista_torneos')
    return render(request, 'torneos/crear.html', {'form': form})

def editar_torneo(request, id):
    torneo = get_object_or_404(Torneo, id=id)
    form = TorneoForm(request.POST or None, instance=torneo)
    if form.is_valid():
        form.save()
        return redirect('lista_torneos')
    return render(request, 'torneos/editar.html', {'form': form})

def eliminar_torneo(request, id):
    torneo = get_object_or_404(Torneo, id=id)
    torneo.delete()
    return redirect('lista_torneos')
