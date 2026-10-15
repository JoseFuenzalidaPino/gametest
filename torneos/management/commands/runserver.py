from django.contrib.staticfiles.management.commands.runserver import Command as RunserverCommand


class Command(RunserverCommand):
    """`manage.py runserver` escucha en todas las interfaces (0.0.0.0:8000) para
    que el sitio sea accesible desde otros equipos de la red local.
    Para limitarlo a este equipo: `manage.py runserver 127.0.0.1:8000`."""

    default_addr = '0.0.0.0'
