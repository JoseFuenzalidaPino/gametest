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


CLAVE = 'TorneoSeguro2026'


class PaginasPublicasTests(TestCase):
    def test_rutas_de_login_y_registro(self):
        self.assertEqual(reverse('login'), '/')
        self.assertEqual(reverse('registro'), '/register/')

    def test_login_y_registro_cargan_con_formulario(self):
        resp = self.client.get('/')
        self.assertContains(resp, 'name="username"')
        self.assertContains(resp, 'name="password"')
        resp = self.client.get('/register/')
        self.assertContains(resp, 'name="password1"')
        self.assertContains(resp, 'name="password2"')

    def test_lista_carga_con_torneos(self):
        crear_torneo()
        self.assertEqual(self.client.get(reverse('lista_torneos')).status_code, 200)


class RegistroTests(TestCase):
    def registrar(self, username='ana', password1=CLAVE, password2=CLAVE):
        return self.client.post(reverse('registro'), {
            'username': username, 'password1': password1, 'password2': password2})

    def test_registro_crea_usuario_jugador_y_grupo(self):
        resp = self.registrar(username='ana')
        self.assertRedirects(resp, reverse('login'), fetch_redirect_response=False)
        user = User.objects.get(username='ana')
        self.assertTrue(user.groups.filter(name='Usuarios').exists())
        self.assertTrue(Jugador.objects.filter(user=user, nickname='ana').exists())
        self.assertContains(self.client.get(resp.url), 'Cuenta creada')

    def test_registro_rechaza_usuario_duplicado(self):
        User.objects.create_user('ana', password='x')
        self.assertEqual(self.registrar(username='ana').status_code, 200)
        self.assertEqual(User.objects.filter(username='ana').count(), 1)

    def test_registro_rechaza_contrasenas_distintas(self):
        resp = self.registrar(password2='OtraDistinta2026')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context['form'].has_error('password2'))
        self.assertFalse(User.objects.filter(username='ana').exists())

    def test_registro_rechaza_contrasena_debil(self):
        self.assertEqual(self.registrar(password1='123', password2='123').status_code, 200)
        self.assertFalse(User.objects.filter(username='ana').exists())

    def test_usuario_con_sesion_va_a_su_panel(self):
        User.objects.create_user('ana', password=CLAVE)
        self.client.login(username='ana', password=CLAVE)
        self.assertRedirects(self.client.get('/register/'), reverse('jugador_panel'))
        self.assertRedirects(self.client.get('/'), reverse('jugador_panel'))


class LoginTests(TestCase):
    def test_login_jugador_va_a_su_panel(self):
        User.objects.create_user('ana', password=CLAVE)
        resp = self.client.post(reverse('login'), {'username': 'ana', 'password': CLAVE})
        self.assertRedirects(resp, reverse('jugador_panel'))

    def test_login_admin_va_al_panel_admin(self):
        user = User.objects.create_user('jefe', password=CLAVE)
        user.groups.add(Group.objects.get(name='Administrador'))
        resp = self.client.post(reverse('login'), {'username': 'jefe', 'password': CLAVE})
        self.assertRedirects(resp, reverse('admin_panel'))

    def test_login_respeta_next_local_y_no_externo(self):
        User.objects.create_user('ana', password=CLAVE)
        datos = {'username': 'ana', 'password': CLAVE}
        resp = self.client.post('/', {**datos, 'next': '/torneos/'})
        self.assertRedirects(resp, '/torneos/')
        self.client.logout()
        resp = self.client.post('/', {**datos, 'next': 'https://malicioso.com/'})
        self.assertRedirects(resp, reverse('jugador_panel'))

    def test_login_incorrecto(self):
        resp = self.client.post(reverse('login'), {'username': 'nadie', 'password': 'x'})
        self.assertContains(resp, 'Usuario o contraseña incorrectos')

    def test_logout(self):
        User.objects.create_user('ana', password=CLAVE)
        self.client.login(username='ana', password=CLAVE)
        self.assertRedirects(self.client.get(reverse('logout')), reverse('login'))
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
        resp = self.client.post(f"{reverse('login')}?next={url}", {'username': 'ana', 'password': 'clave123'})
        self.assertRedirects(resp, url, target_status_code=200)

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
