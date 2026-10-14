from django.shortcuts import render, redirect, get_object_or_404
from .models import Torneo
from .forms import TorneoForm
from rest_framework import viewsets
from .serializers import TorneoSerializer
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User, Group
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Torneo, Inscripcion

@login_required
def inscribirse_torneo(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    jugador = request.user

    if Inscripcion.objects.filter(torneo=torneo, jugador=jugador).exists():
        return render(request, 'torneos/mensaje.html', {'mensaje': 'Ya estás inscrito en este torneo.'})

    inscripciones_actuales = Inscripcion.objects.filter(torneo=torneo).count()
    if inscripciones_actuales >= torneo.cupos_disponibles:
        return render(request, 'torneos/mensaje.html', {'mensaje': 'No hay cupos disponibles.'})

    Inscripcion.objects.create(torneo=torneo, jugador=jugador)
    return render(request, 'torneos/mensaje.html', {'mensaje': 'Inscripción exitosa.'})


def registrar_usuario(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        if User.objects.filter(username=username).exists():
            return render(request, "usuarios/registro.html", {"error": "El usuario ya existe"})
        user = User.objects.create_user(username=username, password=password)
        grupo_jugador = Group.objects.get(name="Usuarios")  # asigna rol Jugador
        user.groups.add(grupo_jugador)
        return redirect("login")
    return render(request, "usuarios/registro.html")

def iniciar_sesion(request):
    mensaje = ""
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.groups.filter(name="Administrador").exists():
                return redirect("admin_panel")   # si es admin, va a su panel
            else:
                return redirect("jugador_panel") # si es jugador, va a su panel
        else:
            mensaje = "Usuario o contraseña incorrectos"
    return render(request, "usuarios/login.html", {"mensaje": mensaje})

@login_required
def cerrar_sesion(request):
    logout(request)
    return redirect("login")

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

def inicio(request):
    torneos = Torneo.objects.all().order_by('-fecha')[:3]  # muestra los 3 más recientes
    return render(request, 'torneos/index.html', {'torneos': torneos})
