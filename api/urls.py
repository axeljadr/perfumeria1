from django.urls import path
from . import views

urlpatterns = [
 path('api/crear/perfumes', views.crear_perfume_completo, name='crear_perfume_completo'),
]