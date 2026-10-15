from datetime import date

from rest_framework import serializers
from .models import Torneo


class TorneoSerializer(serializers.ModelSerializer):
    inscritos = serializers.SerializerMethodField()

    class Meta:
        model = Torneo
        fields = ['id', 'nombre', 'videojuego', 'fecha', 'max_participantes',
                  'descripcion', 'estado', 'inscritos']

    def get_inscritos(self, torneo):
        return torneo.inscritos_count()

    def validate_fecha(self, fecha):
        cambio = self.instance is None or fecha != self.instance.fecha
        if cambio and fecha < date.today():
            raise serializers.ValidationError('La fecha no puede ser anterior a hoy.')
        return fecha

    def validate_max_participantes(self, maximo):
        if self.instance is not None and maximo < self.instance.inscritos_count():
            raise serializers.ValidationError('No puede ser menor a los jugadores ya inscritos.')
        return maximo
