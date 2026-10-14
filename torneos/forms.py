from django import forms
from .models import Torneo

class TorneoForm(forms.ModelForm):
    class Meta:
        model = Torneo
        fields = ['nombre', 'videojuego', 'fecha', 'max_participantes', 'descripcion', 'estado']
