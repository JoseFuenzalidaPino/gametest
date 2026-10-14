from django.contrib import admin
from .models import Jugador, Torneo, Inscripcion, Resultado

# 🔹 Personalización del panel para el modelo Jugador
@admin.register(Jugador)
class JugadorAdmin(admin.ModelAdmin):
    list_display = ('nickname', 'user')  # columnas visibles
    search_fields = ('nickname', 'user__username')  # búsqueda por nickname o usuario
    list_filter = ('user',)  # filtro por usuario

# 🔹 Personalización del panel para el modelo Torneo
@admin.register(Torneo)
class TorneoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'videojuego', 'fecha', 'estado')
    search_fields = ('nombre', 'videojuego')
    list_filter = ('estado', 'fecha')

# 🔹 Personalización del panel para el modelo Inscripción
@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = ('torneo', 'jugador', 'fecha_inscripcion')
    search_fields = ('torneo__nombre', 'jugador__nickname')
    list_filter = ('torneo', 'fecha_inscripcion')

# 🔹 Personalización del panel para el modelo Resultado
@admin.register(Resultado)
class ResultadoAdmin(admin.ModelAdmin):
    list_display = ('torneo', 'jugador', 'puntaje')
    search_fields = ('torneo__nombre', 'jugador__nickname')
    list_filter = ('torneo',)
