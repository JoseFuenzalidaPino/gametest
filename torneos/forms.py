from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Torneo

class TorneoForm(forms.ModelForm):
    class Meta:
        model = Torneo
        fields = ['nombre', 'videojuego', 'fecha', 'max_participantes', 'descripcion', 'estado']


class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class LoginForm(BootstrapMixin, AuthenticationForm):
    error_messages = {
        'invalid_login': 'Usuario o contraseña incorrectos',
        'inactive': 'Esta cuenta está desactivada',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Usuario'
        self.fields['password'].label = 'Contraseña'


class RegistroForm(BootstrapMixin, UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Usuario'
        self.fields['password1'].label = 'Contraseña'
        self.fields['password2'].label = 'Confirmar contraseña'
        self.fields['password2'].help_text = ''
