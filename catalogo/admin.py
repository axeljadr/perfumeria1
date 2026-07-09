from django.contrib import admin
from .models import (
    FamiliaOlfativa, Acorde, Nota,
    Perfume, ImagenPerfume, Presentacion
)



@admin.register(FamiliaOlfativa)
class FamiliaOlfativaAdmin(admin.ModelAdmin):
    list_display = ['nombre',]
    search_fields = ['nombre']


@admin.register(Acorde)
class AcordeAdmin(admin.ModelAdmin):
    list_display = ['nombre']
    search_fields = ['nombre']


@admin.register(Nota)
class NotaAdmin(admin.ModelAdmin):
    list_display = ['nombre']
    search_fields = ['nombre']


class ImagenPerfumeInline(admin.TabularInline):
    model = ImagenPerfume
    extra = 3  # muestra 3 campos de imagen por defecto
    fields = ['imagen', 'tipo']


@admin.register(Perfume)
class PerfumeAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'marca', 'genero', 'familia_olfativa', 'activo']
    list_filter = ['genero', 'familia_olfativa', 'longevidad', 'estela', 'uso', 'activo']
    search_fields = ['nombre', 'marca']
    filter_horizontal = ['acordes', 'notas']  # selector visual para ManyToMany
    inlines = [ImagenPerfumeInline]
    fieldsets = (
        ('Información básica', {
            'fields': ('nombre', 'marca', 'volumen_ml', 'genero', 'descripcion', 'activo')
        }),
        ('Clasificación olfativa', {
            'fields': ('familia_olfativa', 'acordes', 'notas')
        }),
        ('Perfil olfativo', {
            'fields': ('longevidad', 'estela', 'uso')
        }),
    )




class PresentacionInline(admin.TabularInline):
    model = Presentacion
    extra = 1
    fields = ['tipo', 'volumen_ml', 'precio', 'stock', 'activo']


@admin.register(Presentacion)
class PresentacionAdmin(admin.ModelAdmin):
    list_display = ['perfume', 'tipo', 'volumen_ml', 'precio', 'stock', 'disponible']
    list_filter = ['tipo', 'activo']