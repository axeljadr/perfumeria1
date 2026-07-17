from django.urls import path
from . import views

app_name = 'apartados'

urlpatterns = [
    path('apartados/',                        views.lista_pedidos,    name='lista_pedidos'),
    path('apartados/nuevo/',                  views.crear_pedido,     name='crear'),
    path('api/presentaciones/buscar/',views.buscar_presentaciones,    name='buscar_presentaciones'),
    path('apartados/<int:pk>/',               views.detalle_pedido,   name='detalle'),
    path('apartados/<int:pk>/pago/',          views.registrar_pago,   name='registrar_pago'),
    path('apartados/<int:pk>/estado/',        views.cambiar_estado,   name='cambiar_estado'),
    path('apartados/pago/<int:pk>/eliminar/', views.eliminar_pago,    name='eliminar_pago'),
]