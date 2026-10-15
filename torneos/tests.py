from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .models import Inscripcion, Jugador, Torneo


def crear_torneo(**kwargs):
    datos = dict(nombre='Copa', videojuego='FIFA', fecha=date(2026, 12, 1),
                 max_participantes=2, descripcion='Torneo de prueba')
    datos.update(kwargs)
    return Torneo.objects.create(**datos)


class PaginasPublicasTests(TestCase):
    def test_inicio_y_lista_cargan_con_torneos(self):
        crear_torneo()
        self.assertEqual(self.client.get(reverse('inicio')).status_code, 200)
        self.assertEqual(self.client.get(reverse('lista_torneos')).status_code, 200)

    def test_login_y_registro_cargan(self):
        self.assertEqual(self.client.get(reverse('login')).status_code, 200)
        self.assertEqual(self.client.get(reverse('registro')).status_code, 200)


class RegistroLoginTests(TestCase):
    def test_registro_crea_usuario_jugador_y_grupo(self):
        resp = self.client.post(reverse('registro'), {'username': 'ana', 'password': 'clave123'})
        self.assertContains(resp, 'Cuenta creada')
        user = User.objects.get(username='ana')
        self.assertTrue(user.groups.filter(name='Usuarios').exists())
        self.assertTrue(Jugador.objects.filter(user=user, nickname='ana').exists())

    def test_registro_rechaza_duplicado_y_vacio(self):
        User.objects.create_user('ana', password='x')
        resp = self.client.post(reverse('registro'), {'username': 'ana', 'password': 'y'})
        self.assertContains(resp, 'El usuario ya existe')
        resp = self.client.post(reverse('registro'), {'username': '', 'password': ''})
        self.assertContains(resp, 'obligatorios')

    def test_login_jugador_va_a_su_panel(self):
        User.objects.create_user('ana', password='clave123')
        resp = self.client.post(reverse('login'), {'username': 'ana', 'password': 'clave123'})
        self.assertRedirects(resp, reverse('jugador_panel'))

    def test_login_admin_va_al_panel_admin(self):
        user = User.objects.create_user('jefe', password='clave123')
        user.groups.add(Group.objects.get(name='Administrador'))
        resp = self.client.post(reverse('login'), {'username': 'jefe', 'password': 'clave123'})
        self.assertRedirects(resp, reverse('admin_panel'))

    def test_login_incorrecto(self):
        resp = self.client.post(reverse('login'), {'username': 'nadie', 'password': 'x'})
        self.assertContains(resp, 'incorrectos')

    def test_logout(self):
        User.objects.create_user('ana', password='clave123')
        self.client.login(username='ana', password='clave123')
        self.assertRedirects(self.client.get(reverse('logout')), reverse('inicio'))
        self.assertNotIn('_auth_user_id', self.client.session)


class InscripcionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ana', password='clave123')
        self.client.login(username='ana', password='clave123')

    def inscribir(self, torneo):
        return self.client.get(reverse('inscribirse_torneo', args=[torneo.id]))

    def test_requiere_login(self):
        self.client.logout()
        torneo = crear_torneo()
        url = reverse('inscribirse_torneo', args=[torneo.id])
        self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}")

    def test_inscripcion_exitosa_y_duplicada(self):
        torneo = crear_torneo()
        self.assertContains(self.inscribir(torneo), 'Inscripción exitosa')
        self.assertContains(self.inscribir(torneo), 'Ya estás inscrito')
        self.assertEqual(Inscripcion.objects.filter(torneo=torneo).count(), 1)

    def test_sin_cupos(self):
        torneo = crear_torneo(max_participantes=1)
        otro = Jugador.objects.create(user=User.objects.create_user('otro'), nickname='otro')
        Inscripcion.objects.create(torneo=torneo, jugador=otro)
        self.assertContains(self.inscribir(torneo), 'No hay cupos')

    def test_torneo_no_disponible(self):
        torneo = crear_torneo(estado='FINALIZADO')
        self.assertContains(self.inscribir(torneo), 'no admite inscripciones')

    def test_panel_jugador_muestra_inscripciones(self):
        torneo = crear_torneo(nombre='Copa Especial')
        self.inscribir(torneo)
        self.assertContains(self.client.get(reverse('jugador_panel')), 'Copa Especial')


class AdminPanelTests(TestCase):
    def test_jugador_no_accede(self):
        User.objects.create_user('ana', password='clave123')
        self.client.login(username='ana', password='clave123')
        self.assertEqual(self.client.get(reverse('admin_panel')).status_code, 302)

    def test_admin_accede(self):
        User.objects.create_user('jefe', password='clave123', is_staff=True)
        self.client.login(username='jefe', password='clave123')
        crear_torneo(nombre='Copa Admin')
        self.assertContains(self.client.get(reverse('admin_panel')), 'Copa Admin')
