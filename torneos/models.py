from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.contrib.auth.models import User

class Jugador(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nickname = models.CharField(max_length=50)

    def __str__(self):
        return self.nickname


class Torneo(models.Model):
    ESTADOS = [
        ('DISPONIBLE', 'Disponible'),
        ('COMPLETO', 'Completo'),
        ('EN_CURSO', 'En curso'),
        ('FINALIZADO', 'Finalizado'),
    ]

    nombre = models.CharField(max_length=100)
    videojuego = models.CharField(max_length=100)
    fecha = models.DateField()
    max_participantes = models.IntegerField(validators=[MinValueValidator(2), MaxValueValidator(1000)])
    descripcion = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='DISPONIBLE')
    cupos_disponibles = models.IntegerField(default=10)

    def __str__(self):
        return self.nombre

    def inscritos_count(self):
        return self.inscripcion_set.count()

    def admite_inscripciones(self):
        return self.estado == 'DISPONIBLE'

    def actualizar_estado_por_cupos(self):
        """Marca el torneo como Completo cuando se llenan los cupos."""
        if self.estado == 'DISPONIBLE' and self.inscritos_count() >= self.max_participantes:
            self.estado = 'COMPLETO'
            self.save(update_fields=['estado'])


class Inscripcion(models.Model):
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE)
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE)
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('jugador', 'torneo')


class Resultado(models.Model):
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE)
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE)
    puntaje = models.IntegerField()

