from datetime import date

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Torneo


class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            field.widget.attrs['class'] = css

    def full_clean(self):
        super().full_clean()
        # Marca en rojo (Bootstrap) los campos con errores
        for nombre in self.errors:
            if nombre in self.fields:
                self.fields[nombre].widget.attrs['class'] += ' is-invalid'


class TorneoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Torneo
        fields = ['nombre', 'videojuego', 'fecha', 'max_participantes', 'descripcion', 'estado']
        labels = {
            'nombre': 'Nombre del torneo',
            'videojuego': 'Videojuego',
            'fecha': 'Fecha',
            'max_participantes': 'Máximo de participantes',
            'descripcion': 'Descripción',
            'estado': 'Estado',
        }
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'max_participantes': forms.NumberInput(attrs={'min': 2, 'max': 1000}),
            'descripcion': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        if len(nombre) < 3:
            raise forms.ValidationError('El nombre debe tener al menos 3 caracteres.')
        duplicado = Torneo.objects.filter(nombre__iexact=nombre).exclude(pk=self.instance.pk)
        if duplicado.exists():
            raise forms.ValidationError('Ya existe un torneo con ese nombre.')
        return nombre

    def clean_videojuego(self):
        videojuego = self.cleaned_data['videojuego'].strip()
        if not videojuego:
            raise forms.ValidationError('Debes indicar el videojuego.')
        return videojuego

    def clean_fecha(self):
        fecha = self.cleaned_data['fecha']
        # Al crear o al cambiar la fecha, no se permite una fecha pasada
        cambio = self.instance.pk is None or fecha != self.instance.fecha
        if cambio and fecha < date.today():
            raise forms.ValidationError('La fecha no puede ser anterior a hoy.')
        return fecha

    def clean_descripcion(self):
        descripcion = self.cleaned_data['descripcion'].strip()
        if len(descripcion) < 10:
            raise forms.ValidationError('La descripción debe tener al menos 10 caracteres.')
        return descripcion

    def clean(self):
        datos = super().clean()
        maximo = datos.get('max_participantes')
        estado = datos.get('estado')
        if self.instance.pk and maximo is not None:
            inscritos = self.instance.inscritos_count()
            if maximo < inscritos:
                self.add_error('max_participantes',
                               f'No puede ser menor a los {inscritos} jugadores ya inscritos.')
            elif estado == 'DISPONIBLE' and inscritos >= maximo:
                self.add_error('estado', 'El torneo ya está lleno; usa el estado Completo o aumenta el máximo.')
        return datos


class TorneoFiltroForm(BootstrapMixin, forms.Form):
    videojuego = forms.CharField(required=False, label='Videojuego')
    estado = forms.ChoiceField(required=False, label='Estado',
                               choices=[('', 'Todos')] + Torneo.ESTADOS)
    fecha_desde = forms.DateField(required=False, label='Desde',
                                  widget=forms.DateInput(attrs={'type': 'date'}))
    fecha_hasta = forms.DateField(required=False, label='Hasta',
                                  widget=forms.DateInput(attrs={'type': 'date'}))
    min_participantes = forms.IntegerField(required=False, min_value=0, label='Mín. participantes')

    def filtrar(self, torneos):
        if not self.is_valid():
            return torneos
        d = self.cleaned_data
        if d['videojuego']:
            torneos = torneos.filter(videojuego__icontains=d['videojuego'])
        if d['estado']:
            torneos = torneos.filter(estado=d['estado'])
        if d['fecha_desde']:
            torneos = torneos.filter(fecha__gte=d['fecha_desde'])
        if d['fecha_hasta']:
            torneos = torneos.filter(fecha__lte=d['fecha_hasta'])
        if d['min_participantes'] is not None:
            torneos = torneos.filter(max_participantes__gte=d['min_participantes'])
        return torneos


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
