from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_torneos, name='lista_torneos'),
    path('crear/', views.crear_torneo, name='crear_torneo'),
    path('<int:id>/', views.detalle_torneo, name='detalle_torneo'),
    path('editar/<int:id>/', views.editar_torneo, name='editar_torneo'),
    path('eliminar/<int:id>/', views.eliminar_torneo, name='eliminar_torneo'),
    path('inscribirse/<int:torneo_id>/', views.inscribirse_torneo, name='inscribirse_torneo'),
]
