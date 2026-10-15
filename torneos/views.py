from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db import IntegrityError
from django.db.models import Count
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from rest_framework import viewsets
from .models import Torneo, Inscripcion, Jugador, Resultado
from .forms import TorneoForm, TorneoFiltroForm, LoginForm, RegistroForm
from .permissions import EsAdministradorOSoloLectura
from .roles import es_administrador, admin_requerido
from .serializers import TorneoSerializer


def obtener_jugador(user):
    jugador, _ = Jugador.objects.get_or_create(user=user, defaults={"nickname": user.username})
    return jugador


def torneos_con_inscritos():
    return Torneo.objects.annotate(inscritos=Count('inscripcion'))


# ---------- Inscripciones ----------

@require_POST
@login_required
def inscribirse_torneo(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    jugador = obtener_jugador(request.user)

    if Inscripcion.objects.filter(torneo=torneo, jugador=jugador).exists():
        messages.warning(request, 'Ya estás inscrito en este torneo.')
    elif not torneo.admite_inscripciones():
        messages.error(request, f'Este torneo no admite inscripciones (estado: {torneo.get_estado_display()}).')
    elif torneo.inscritos_count() >= torneo.max_participantes:
        torneo.actualizar_estado_por_cupos()
        messages.error(request, 'No hay cupos disponibles.')
    else:
        try:
            Inscripcion.objects.create(torneo=torneo, jugador=jugador)
        except IntegrityError:  # doble envío simultáneo del formulario
            messages.warning(request, 'Ya estás inscrito en este torneo.')
        else:
            torneo.actualizar_estado_por_cupos()
            messages.success(request, f'Inscripción exitosa en {torneo.nombre}.')
    return redirect('detalle_torneo', id=torneo.id)


# ---------- Sesiones y paneles ----------

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
    """Página de inicio: resumen de torneos y, sin sesión, formulario de login."""
    form = None
    siguiente = request.POST.get("next") or request.GET.get("next", "")
    if not request.user.is_authenticated:
        form = LoginForm(request, data=request.POST or None)
        if form.is_valid():
            login(request, form.get_user())
            if url_has_allowed_host_and_scheme(siguiente, allowed_hosts={request.get_host()}):
                return redirect(siguiente)
            return redirigir_a_panel(form.get_user())

    proximos = (torneos_con_inscritos().filter(fecha__gte=date.today())
                .exclude(estado='FINALIZADO').order_by('fecha')[:6])
    resumen = {
        'total': Torneo.objects.count(),
        'disponibles': Torneo.objects.filter(estado='DISPONIBLE').count(),
        'en_curso': Torneo.objects.filter(estado='EN_CURSO').count(),
        'finalizados': Torneo.objects.filter(estado='FINALIZADO').count(),
        'jugadores': Jugador.objects.count(),
    }
    return render(request, "torneos/inicio.html", {
        "form": form, "next": siguiente, "proximos": proximos, "resumen": resumen,
    })

def cerrar_sesion(request):
    logout(request)
    return redirect("login")

@login_required
def jugador_panel(request):
    inscripciones = (Inscripcion.objects.filter(jugador__user=request.user)
                     .select_related('torneo').order_by('torneo__fecha'))
    return render(request, "usuarios/jugador_panel.html", {"inscripciones": inscripciones})

@admin_requerido
def admin_panel(request):
    torneos = torneos_con_inscritos().order_by('-fecha')
    return render(request, "usuarios/admin_panel.html", {
        "torneos": torneos,
        "total_jugadores": Jugador.objects.count(),
        "total_inscripciones": Inscripcion.objects.count(),
    })


# ---------- API ----------

class TorneoViewSet(viewsets.ModelViewSet):
    queryset = Torneo.objects.all().order_by('fecha')
    serializer_class = TorneoSerializer
    permission_classes = [EsAdministradorOSoloLectura]


# ---------- CRUD de torneos ----------

def lista_torneos(request):
    filtro = TorneoFiltroForm(request.GET or None)
    torneos = filtro.filtrar(torneos_con_inscritos()).order_by('fecha')
    return render(request, 'torneos/lista.html', {'torneos': torneos, 'filtro': filtro})

def detalle_torneo(request, id):
    torneo = get_object_or_404(Torneo, id=id)
    inscripciones = torneo.inscripcion_set.select_related('jugador__user').order_by('fecha_inscripcion')
    resultados = (Resultado.objects.filter(torneo=torneo)
                  .select_related('jugador').order_by('-puntaje'))
    inscrito = (request.user.is_authenticated
                and inscripciones.filter(jugador__user=request.user).exists())
    return render(request, 'torneos/detalle.html', {
        'torneo': torneo,
        'inscripciones': inscripciones,
        'resultados': resultados,
        'inscrito': inscrito,
        'cupos_libres': max(torneo.max_participantes - inscripciones.count(), 0),
    })

@admin_requerido
def crear_torneo(request):
    form = TorneoForm(request.POST or None)
    if form.is_valid():
        torneo = form.save()
        messages.success(request, f'Torneo "{torneo.nombre}" creado correctamente.')
        return redirect('detalle_torneo', id=torneo.id)
    return render(request, 'torneos/crear.html', {'form': form})

@admin_requerido
def editar_torneo(request, id):
    torneo = get_object_or_404(Torneo, id=id)
    form = TorneoForm(request.POST or None, instance=torneo)
    if form.is_valid():
        form.save()
        messages.success(request, f'Torneo "{torneo.nombre}" actualizado.')
        return redirect('detalle_torneo', id=torneo.id)
    return render(request, 'torneos/editar.html', {'form': form, 'torneo': torneo})

@admin_requerido
def eliminar_torneo(request, id):
    torneo = get_object_or_404(Torneo, id=id)
    if request.method == 'POST':
        nombre = torneo.nombre
        torneo.delete()
        messages.success(request, f'Torneo "{nombre}" eliminado.')
        return redirect('lista_torneos')
    return render(request, 'torneos/eliminar.html', {'torneo': torneo})
