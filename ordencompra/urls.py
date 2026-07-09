from django.urls import path
from . import views

urlpatterns = [# Proveedores
path('proveedores/', views.proveedores_lista, name='proveedores_lista'),
path('proveedores/<int:pk>/editar/', views.proveedor_editar, name='proveedor_editar'),
path('proveedores/<int:pk>/eliminar/', views.proveedor_eliminar, name='proveedor_eliminar'),

# Cotizaciones
path('cotizaciones/', views.cotizaciones_lista, name='cotizaciones_lista'),
path('cotizaciones/<int:pk>/', views.cotizacion_detalle, name='cotizacion_detalle'),
path('cotizaciones/<int:pk>/guardar/', views.cotizacion_guardar_precios, name='cotizacion_guardar_precios'),
path('cotizaciones/<int:pk>/fila/agregar/', views.cotizacion_agregar_fila, name='cotizacion_agregar_fila'),
path('cotizaciones/fila/<int:pk>/eliminar/', views.cotizacion_eliminar_fila, name='cotizacion_eliminar_fila'),
path('cotizaciones/<int:pk>/columna/agregar/', views.cotizacion_agregar_columna, name='cotizacion_agregar_columna'),
path('cotizaciones/columna/<int:pk>/eliminar/', views.cotizacion_eliminar_columna, name='cotizacion_eliminar_columna'),
path('cotizaciones/<int:pk>/cerrar/', views.cotizacion_cerrar, name='cotizacion_cerrar'),
path('cotizaciones/<int:pk>/eliminar/', views.cotizacion_eliminar, name='cotizacion_eliminar'),
]