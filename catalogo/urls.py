from django.urls import path
from . import views


urlpatterns = [
    path('', views.catalogo, name='catalogo'),
    path('perfume/<int:pk>/', views.detalle_perfume, name='detalle_perfume'),
    path('perfume/nuevo/', views.crear_perfume, name='crear_perfume'),
    path('perfume/<int:pk>/editar/', views.editar_perfume, name='editar_perfume'),

    # Familias olfativas
    path('familias/', views.familias_lista, name='familias_lista'), 
    path('familias/<int:pk>/editar/', views.familia_editar, name='familia_editar'),
    path('familias/<int:pk>/eliminar/', views.familia_eliminar, name='familia_eliminar'),

    # Acordes
    path('acordes/', views.acordes_lista, name='acordes_lista'),
    path('acordes/<int:pk>/editar/', views.acorde_editar, name='acorde_editar'),
    path('acordes/<int:pk>/eliminar/', views.acorde_eliminar, name='acorde_eliminar'),

    # Notas
    path('notas/', views.notas_lista, name='notas_lista'),
    path('notas/<int:pk>/editar/', views.nota_editar, name='nota_editar'),
    path('notas/<int:pk>/eliminar/', views.nota_eliminar, name='nota_eliminar'),

    path('perfume/<int:perfume_pk>/presentacion/nueva/', views.presentacion_crear, name='presentacion_crear'),
    path('presentacion/<int:pk>/editar/', views.presentacion_editar, name='presentacion_editar'),
    path('presentacion/<int:pk>/eliminar/', views.presentacion_eliminar, name='presentacion_eliminar'),

    path('api/familia/buscar/',  views.buscar_familia,  name='buscar_familia'),
    path('api/familia/crear/',   views.crear_familia,   name='crear_familia'),
    path('api/acorde/buscar/',   views.buscar_acorde,   name='buscar_acorde'),
    path('api/acorde/crear/',    views.crear_acorde,    name='crear_acorde'),
    path('api/nota/buscar/',     views.buscar_nota,     name='buscar_nota'),
    path('api/nota/crear/',      views.crear_nota,      name='crear_nota'),

]