from django.urls import path
from . import views
app_name = 'contabilidad'


urlpatterns = [
    # Dashboard
    path('Dashboard/', views.dashboard, name='dashboard'),
    
    # Compras
    path('compras/', views.compra_list, name='compra_list'),
    path('compras/nueva/', views.compra_create, name='compra_create'),
    path('compras/<int:pk>/', views.compra_detail, name='compra_detail'),
    path('compras/<int:pk>/procesar/', views.compra_procesar, name='compra_procesar'),
    path('compras/<int:pk>/eliminar/', views.compra_delete, name='compra_delete'),
    
    # Presentaciones
    path('presentaciones/', views.presentacion_list, name='presentacion_list'),
    path('presentaciones/<int:pk>/editar/', views.presentacion_update, name='presentacion_update'),
    path('presentaciones/crear-multiple/', views.presentacion_batch_create, name='presentacion_batch_create'),
    
    # Movimientos contables
    path('movimientos/', views.movimiento_list, name='movimiento_list'),
    path('movimientos/nuevo/', views.movimiento_create, name='movimiento_create'),
    path('movimientos/<int:pk>/editar/', views.movimiento_update, name='movimiento_update'),
    path('movimientos/<int:pk>/eliminar/', views.movimiento_delete, name='movimiento_delete'),
    
    # Configuración
    path('configuracion/', views.configuracion_edit, name='configuracion'),
    
    # Reportes
    path('reportes/', views.reportes, name='reportes'),
]