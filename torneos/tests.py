from datetime import date, timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Inscripcion, Jugador, Resultado, Torneo

CLAVE = 'TorneoSeguro2026'
MANANA = date.today() + timedelta(days=1)


def crear_torneo(**kwargs):
    datos = dict(nombre='Copa', videojuego='FIFA', fecha=MANANA,
                 max_participantes=2, descripcion='Torneo de prueba')
    datos.update(kwargs)
    return Torneo.objects.create(**datos)


def crear_jugador(username):
    return Jugador.objects.create(user=User.objects.create_user(username), nickname=username)


def datos_torneo(**kwargs):
    datos = dict(nombre='Liga Nueva', videojuego='Valorant', fecha=MANANA.isoformat(),
                 max_participantes=8, descripcion='Descripción suficientemente larga',
                 estado='DISPONIBLE')
    datos.update(kwargs)
    return datos


class ConSesionMixin:
    def login_jugador(self, username='ana'):
        User.objects.create_user(username, password=CLAVE)
        self.client.login(username=username, password=CLAVE)

    def login_admin(self, username='jefe'):
        user = User.objects.create_user(username, password=CLAVE)
        user.groups.add(Group.objects.get(name='Administrador'))
        self.client.login(username=username, password=CLAVE)


class InicioTests(ConSesionMixin, TestCase):
    def test_rutas_de_login_y_registro(self):
        self.assertEqual(reverse('login'), '/')
        self.assertEqual(reverse('registro'), '/register/')

    def test_inicio_muestra_resumen_y_login(self):
        crear_torneo(nombre='Copa Próxima')
        crear_torneo(nombre='Copa Vieja', fecha=date.today() - timedelta(days=5), estado='FINALIZADO')
        resp = self.client.get('/')
        self.assertContains(resp, 'Copa Próxima')
        self.assertNotContains(resp, 'Copa Vieja')
        self.assertEqual(resp.context['resumen']['total'], 2)
        self.assertEqual(resp.context['resumen']['finalizados'], 1)
        self.assertContains(resp, 'name="username"')

    def test_inicio_con_sesion_muestra_resumen_sin_login(self):
        self.login_jugador()
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'name="password"')

    def test_registro_carga_con_formulario(self):
        resp = self.client.get('/register/')
        self.assertContains(resp, 'name="password1"')
        self.assertContains(resp, 'name="password2"')

    def test_base_responsiva(self):
        self.assertContains(self.client.get('/'), 'name="viewport"')


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
        self.assertTrue(resp.context['form'].has_error('password2'))
        self.assertFalse(User.objects.filter(username='ana').exists())

    def test_registro_rechaza_contrasena_debil(self):
        self.assertEqual(self.registrar(password1='123', password2='123').status_code, 200)
        self.assertFalse(User.objects.filter(username='ana').exists())

    def test_usuario_con_sesion_no_ve_registro(self):
        User.objects.create_user('ana', password=CLAVE)
        self.client.login(username='ana', password=CLAVE)
        self.assertRedirects(self.client.get('/register/'), reverse('jugador_panel'))


class LoginTests(ConSesionMixin, TestCase):
    def test_login_jugador_va_a_su_panel(self):
        User.objects.create_user('ana', password=CLAVE)
        resp = self.client.post('/', {'username': 'ana', 'password': CLAVE})
        self.assertRedirects(resp, reverse('jugador_panel'))

    def test_login_admin_va_al_panel_admin(self):
        user = User.objects.create_user('jefe', password=CLAVE)
        user.groups.add(Group.objects.get(name='Administrador'))
        resp = self.client.post('/', {'username': 'jefe', 'password': CLAVE})
        self.assertRedirects(resp, reverse('admin_panel'))

    def test_login_respeta_next_local_y_no_externo(self):
        User.objects.create_user('ana', password=CLAVE)
        datos = {'username': 'ana', 'password': CLAVE}
        self.assertRedirects(self.client.post('/', {**datos, 'next': '/torneos/'}), '/torneos/')
        self.client.logout()
        resp = self.client.post('/', {**datos, 'next': 'https://malicioso.com/'})
        self.assertRedirects(resp, reverse('jugador_panel'))

    def test_login_incorrecto(self):
        resp = self.client.post('/', {'username': 'nadie', 'password': 'x'})
        self.assertContains(resp, 'Usuario o contraseña incorrectos')

    def test_logout(self):
        self.login_jugador()
        self.assertRedirects(self.client.get(reverse('logout')), reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)


class ListaYDetalleTests(TestCase):
    def setUp(self):
        self.fifa = crear_torneo(nombre='Copa FIFA', videojuego='FIFA 26', max_participantes=16)
        self.lol = crear_torneo(nombre='Liga LoL', videojuego='League of Legends',
                                fecha=MANANA + timedelta(days=30), estado='EN_CURSO', max_participantes=4)

    def nombres(self, **filtros):
        resp = self.client.get(reverse('lista_torneos'), filtros)
        return {t.nombre for t in resp.context['torneos']}

    def test_lista_muestra_detalles(self):
        resp = self.client.get(reverse('lista_torneos'))
        self.assertContains(resp, 'League of Legends')
        self.assertContains(resp, 'En curso')
        self.assertContains(resp, '0 / 16')

    def test_filtros(self):
        self.assertEqual(self.nombres(videojuego='fifa'), {'Copa FIFA'})
        self.assertEqual(self.nombres(estado='EN_CURSO'), {'Liga LoL'})
        self.assertEqual(self.nombres(fecha_desde=(MANANA + timedelta(days=1)).isoformat()), {'Liga LoL'})
        self.assertEqual(self.nombres(fecha_hasta=MANANA.isoformat()), {'Copa FIFA'})
        self.assertEqual(self.nombres(min_participantes=10), {'Copa FIFA'})
        self.assertEqual(self.nombres(), {'Copa FIFA', 'Liga LoL'})

    def test_detalle_muestra_inscritos_y_resultados(self):
        jugador = crear_jugador('pedro')
        Inscripcion.objects.create(torneo=self.fifa, jugador=jugador)
        Resultado.objects.create(torneo=self.fifa, jugador=jugador, puntaje=42)
        resp = self.client.get(reverse('detalle_torneo', args=[self.fifa.id]))
        self.assertContains(resp, 'pedro')
        self.assertContains(resp, '42 pts')
        self.assertContains(resp, 'Torneo de prueba')

    def test_detalle_inexistente_da_404(self):
        self.assertEqual(self.client.get(reverse('detalle_torneo', args=[9999])).status_code, 404)


class PermisosCrudTests(ConSesionMixin, TestCase):
    def setUp(self):
        self.torneo = crear_torneo()
        self.urls = [reverse('crear_torneo'),
                     reverse('editar_torneo', args=[self.torneo.id]),
                     reverse('eliminar_torneo', args=[self.torneo.id])]

    def test_anonimo_va_al_login(self):
        for url in self.urls:
            self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}")
        self.client.post(self.urls[2])
        self.assertTrue(Torneo.objects.filter(id=self.torneo.id).exists())

    def test_jugador_recibe_403(self):
        self.login_jugador()
        for url in self.urls:
            self.assertEqual(self.client.get(url).status_code, 403)
        self.client.post(self.urls[2])
        self.assertTrue(Torneo.objects.filter(id=self.torneo.id).exists())

    def test_admin_accede(self):
        self.login_admin()
        for url in self.urls:
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_panel_admin_solo_admin(self):
        self.login_jugador()
        self.assertEqual(self.client.get(reverse('admin_panel')).status_code, 403)

    @override_settings(DEBUG=False)
    def test_paginas_de_error_propias(self):
        self.login_jugador()
        self.assertContains(self.client.get(self.urls[0]), 'No tienes permisos', status_code=403)
        resp = self.client.get(reverse('detalle_torneo', args=[9999]))
        self.assertContains(resp, 'no existe', status_code=404)


class CrudTorneoTests(ConSesionMixin, TestCase):
    def setUp(self):
        self.login_admin()

    def test_crear_valido(self):
        resp = self.client.post(reverse('crear_torneo'), datos_torneo())
        torneo = Torneo.objects.get(nombre='Liga Nueva')
        self.assertRedirects(resp, reverse('detalle_torneo', args=[torneo.id]))

    def test_crear_invalido_muestra_errores(self):
        resp = self.client.post(reverse('crear_torneo'), datos_torneo(
            nombre='ab', fecha='2020-01-01', max_participantes=-5, descripcion='corta'))
        self.assertEqual(resp.status_code, 200)
        form = resp.context['form']
        for campo in ('nombre', 'fecha', 'max_participantes', 'descripcion'):
            self.assertTrue(form.has_error(campo), campo)
        self.assertContains(resp, 'is-invalid')
        self.assertContains(resp, 'La fecha no puede ser anterior a hoy.')
        self.assertFalse(Torneo.objects.filter(nombre='ab').exists())

    def test_crear_nombre_duplicado(self):
        crear_torneo(nombre='Liga Nueva')
        resp = self.client.post(reverse('crear_torneo'), datos_torneo(nombre='liga nueva'))
        self.assertTrue(resp.context['form'].has_error('nombre'))

    def test_editar_no_baja_maximo_bajo_inscritos(self):
        torneo = crear_torneo(max_participantes=5)
        for nombre in ('a', 'b', 'c'):
            Inscripcion.objects.create(torneo=torneo, jugador=crear_jugador(nombre))
        url = reverse('editar_torneo', args=[torneo.id])
        resp = self.client.post(url, datos_torneo(nombre='Copa', max_participantes=2))
        self.assertTrue(resp.context['form'].has_error('max_participantes'))

    def test_editar_torneo_pasado_sin_cambiar_fecha(self):
        torneo = crear_torneo(fecha=date.today() - timedelta(days=3), estado='EN_CURSO')
        url = reverse('editar_torneo', args=[torneo.id])
        resp = self.client.post(url, datos_torneo(nombre='Copa', fecha=torneo.fecha.isoformat(), estado='FINALIZADO'))
        self.assertRedirects(resp, reverse('detalle_torneo', args=[torneo.id]))
        torneo.refresh_from_db()
        self.assertEqual(torneo.estado, 'FINALIZADO')

    def test_eliminar_pide_confirmacion(self):
        torneo = crear_torneo()
        url = reverse('eliminar_torneo', args=[torneo.id])
        self.assertContains(self.client.get(url), 'Sí, eliminar')
        self.assertTrue(Torneo.objects.filter(id=torneo.id).exists())
        self.assertRedirects(self.client.post(url), reverse('lista_torneos'))
        self.assertFalse(Torneo.objects.filter(id=torneo.id).exists())


class InscripcionTests(ConSesionMixin, TestCase):
    def setUp(self):
        self.login_jugador()

    def inscribir(self, torneo):
        return self.client.post(reverse('inscribirse_torneo', args=[torneo.id]), follow=True)

    def test_requiere_login(self):
        self.client.logout()
        torneo = crear_torneo()
        url = reverse('inscribirse_torneo', args=[torneo.id])
        self.assertRedirects(self.client.post(url), f"{reverse('login')}?next={url}")

    def test_requiere_post(self):
        torneo = crear_torneo()
        self.assertEqual(self.client.get(reverse('inscribirse_torneo', args=[torneo.id])).status_code, 405)

    def test_inscripcion_exitosa_y_duplicada(self):
        torneo = crear_torneo(max_participantes=5)
        self.assertContains(self.inscribir(torneo), 'Inscripción exitosa')
        self.assertContains(self.inscribir(torneo), 'Ya estás inscrito')
        self.assertEqual(Inscripcion.objects.filter(torneo=torneo).count(), 1)

    def test_ultimo_cupo_marca_completo(self):
        torneo = crear_torneo(max_participantes=2)
        Inscripcion.objects.create(torneo=torneo, jugador=crear_jugador('otro'))
        self.assertContains(self.inscribir(torneo), 'Inscripción exitosa')
        torneo.refresh_from_db()
        self.assertEqual(torneo.estado, 'COMPLETO')

    def test_sin_cupos(self):
        torneo = crear_torneo(max_participantes=2)
        for nombre in ('otro1', 'otro2'):
            Inscripcion.objects.create(torneo=torneo, jugador=crear_jugador(nombre))
        self.assertContains(self.inscribir(torneo), 'No hay cupos')
        torneo.refresh_from_db()
        self.assertEqual(torneo.estado, 'COMPLETO')

    def test_torneo_no_disponible(self):
        torneo = crear_torneo(estado='FINALIZADO')
        self.assertContains(self.inscribir(torneo), 'no admite inscripciones')
        self.assertFalse(Inscripcion.objects.filter(torneo=torneo).exists())

    def test_torneo_inexistente_da_404(self):
        self.assertEqual(self.client.post(reverse('inscribirse_torneo', args=[9999])).status_code, 404)

    def test_panel_jugador_muestra_inscripciones(self):
        torneo = crear_torneo(nombre='Copa Especial')
        self.inscribir(torneo)
        self.assertContains(self.client.get(reverse('jugador_panel')), 'Copa Especial')


class ApiTests(ConSesionMixin, TestCase):
    def setUp(self):
        self.torneo = crear_torneo()
        self.url = '/api/torneos/'

    def test_anonimo_no_accede(self):
        self.assertIn(self.client.get(self.url).status_code, (401, 403))

    def test_jugador_solo_lee(self):
        self.login_jugador()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()[0]['inscritos'], 0)
        self.assertEqual(self.client.post(self.url, datos_torneo()).status_code, 403)
        self.assertEqual(self.client.delete(f'{self.url}{self.torneo.id}/').status_code, 403)

    def test_admin_crea_y_valida(self):
        self.login_admin()
        self.assertEqual(self.client.post(self.url, datos_torneo()).status_code, 201)
        resp = self.client.post(self.url, datos_torneo(nombre='Otra', fecha='2020-01-01', max_participantes=0))
        self.assertEqual(resp.status_code, 400)
        self.assertIn('fecha', resp.json())
        self.assertIn('max_participantes', resp.json())

    def test_basic_auth(self):
        User.objects.create_user('ana', password=CLAVE)
        resp = self.client.get(self.url, HTTP_AUTHORIZATION='Basic YW5hOlRvcm5lb1NlZ3VybzIwMjY=')
        self.assertEqual(resp.status_code, 200)
