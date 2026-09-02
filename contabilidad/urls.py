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
    path('compras/<int:pk>/editar/', views.compra_update, name='compra_update'),
    path('compras/<int:pk>/eliminar/', views.compra_delete, name='compra_delete'),
    # Nueva adquisición: pantalla para elegir categoría
    path('compras/nueva/',views.adquisicion_nueva,name='adquisicion_nueva'),
    path('compras/perfume/nueva/',views.compra_create,name='compra_create'),
    path('compras/decant/nueva/',views.compra_decant_create,name='compra_decant_create'),
    path('compras/insumo/nueva/',views.compra_insumo_create,name='compra_insumo_create'),
    # Presentaciones
    path('presentaciones/', views.presentacion_list, name='presentacion_list'),
    path('presentaciones/<int:pk>/editar/', views.presentacion_update, name='presentacion_update'),
    path('presentaciones/crear-multiple/', views.presentacion_batch_create, name='presentacion_batch_create'),
    path('presentaciones/get-by-perfume/', views.presentacion_get_by_perfume, name='presentacion_get_by_perfume'),
path('presentaciones/calcular-decants/', views.calcular_decants_ajax, name='calcular_decants_ajax'),
# Lista de precios PDF
    path('presentaciones/lista-precios/', views.lista_precios_selector, name='lista_precios_selector'),
    path('presentaciones/lista-precios/pdf/', views.lista_precios_pdf, name='lista_precios_pdf'),
    path('presentaciones/lista-precios/json/', views.lista_precios_perfumes_json, name='lista_precios_perfumes_json'),
    
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