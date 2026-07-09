from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from .models import Proveedor, Cotizacion, FilaCotizacion, ColumnaCotizacion, CeldaCotizacion
from .forms import  ProveedorForm, CotizacionForm
import json


# ── PROVEEDORES ──────────────────────────────────────────────────

@staff_member_required
def proveedores_lista(request):
    proveedores = Proveedor.objects.all()
    form = ProveedorForm()

    if request.method == 'POST':
        form = ProveedorForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('proveedores_lista')

    return render(request, 'proveedores.html', {
        'proveedores': proveedores,
        'form': form,
    })


@staff_member_required
def proveedor_editar(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    form = ProveedorForm(request.POST or None, instance=proveedor)
    if form.is_valid():
        form.save()
        return redirect('proveedores_lista')
    return render(request, 'edit_item.html', {
        'form': form,
        'titulo': f'Editar proveedor: {proveedor.nombre}',
        'cancelar_url': 'proveedores_lista',
    })


@staff_member_required
def proveedor_eliminar(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    if request.method == 'POST':
        proveedor.delete()
        return redirect('proveedores_lista')
    return render(request, 'confirmar_eliminar.html', {
        'objeto': proveedor.nombre,
        'cancelar_url': 'proveedores_lista',
    })


# ── COTIZACIONES ─────────────────────────────────────────────────

@staff_member_required
def cotizaciones_lista(request):
    cotizaciones = Cotizacion.objects.all()
    form = CotizacionForm()

    if request.method == 'POST':
        form = CotizacionForm(request.POST)
        if form.is_valid():
            cotizacion = form.save()
            return redirect('cotizacion_detalle', pk=cotizacion.pk)

    return render(request, 'cotizaciones_lista.html', {
        'cotizaciones': cotizaciones,
        'form': form,
    })


@staff_member_required
def cotizacion_detalle(request, pk):
    cotizacion = get_object_or_404(Cotizacion, pk=pk)
    filas = cotizacion.filas.all()
    columnas = cotizacion.columnas.select_related('proveedor').all()
    proveedores_disponibles = Proveedor.objects.exclude(
        id__in=columnas.values_list('proveedor_id', flat=True)
    )

    # Construir matriz de celdas
    tabla = []
    for fila in filas:
        celdas_fila = {}
        for columna in columnas:
            celda, _ = CeldaCotizacion.objects.get_or_create(fila=fila, columna=columna)
            celdas_fila[columna.pk] = celda
        tabla.append({'fila': fila, 'celdas': celdas_fila})

    return render(request, 'cotizacion_detalle.html', {
        'cotizacion': cotizacion,
        'filas': filas,
        'columnas': columnas,
        'tabla': tabla,
        'proveedores_disponibles': proveedores_disponibles,
    })


@staff_member_required
def cotizacion_guardar_precios(request, pk):
    """Guarda todos los precios y envíos de la tabla via POST"""
    if request.method != 'POST':
        return redirect('cotizacion_detalle', pk=pk)

    cotizacion = get_object_or_404(Cotizacion, pk=pk)

    # Guardar precios de celdas
    for key, value in request.POST.items():
        if key.startswith('celda_'):
            celda_pk = key.replace('celda_', '')
            try:
                celda = CeldaCotizacion.objects.get(pk=celda_pk)
                celda.precio = value if value.strip() else None
                celda.save()
            except CeldaCotizacion.DoesNotExist:
                pass

        if key.startswith('envio_'):
            columna_pk = key.replace('envio_', '')
            try:
                columna = ColumnaCotizacion.objects.get(pk=columna_pk)
                columna.envio = value if value.strip() else 0
                columna.save()
            except ColumnaCotizacion.DoesNotExist:
                pass

    return redirect('cotizacion_detalle', pk=pk)


@staff_member_required
def cotizacion_agregar_fila(request, pk):
    cotizacion = get_object_or_404(Cotizacion, pk=pk)
    if request.method == 'POST':
        nombre = request.POST.get('perfume_nombre', '').strip()
        if nombre:
            orden = cotizacion.filas.count()
            fila = FilaCotizacion.objects.create(
                cotizacion=cotizacion,
                perfume_nombre=nombre,
                orden=orden
            )
            # Crear celdas vacías para todas las columnas existentes
            for columna in cotizacion.columnas.all():
                CeldaCotizacion.objects.get_or_create(fila=fila, columna=columna)
    return redirect('cotizacion_detalle', pk=pk)


@staff_member_required
def cotizacion_eliminar_fila(request, pk):
    fila = get_object_or_404(FilaCotizacion, pk=pk)
    cotizacion_pk = fila.cotizacion.pk
    fila.delete()
    return redirect('cotizacion_detalle', pk=cotizacion_pk)


@staff_member_required
def cotizacion_agregar_columna(request, pk):
    cotizacion = get_object_or_404(Cotizacion, pk=pk)
    if request.method == 'POST':
        proveedor_pk = request.POST.get('proveedor_id')
        if proveedor_pk:
            proveedor = get_object_or_404(Proveedor, pk=proveedor_pk)
            columna, created = ColumnaCotizacion.objects.get_or_create(
                cotizacion=cotizacion,
                proveedor=proveedor
            )
            if created:
                # Crear celdas vacías para todas las filas existentes
                for fila in cotizacion.filas.all():
                    CeldaCotizacion.objects.get_or_create(fila=fila, columna=columna)
    return redirect('cotizacion_detalle', pk=pk)


@staff_member_required
def cotizacion_eliminar_columna(request, pk):
    columna = get_object_or_404(ColumnaCotizacion, pk=pk)
    cotizacion_pk = columna.cotizacion.pk
    columna.delete()
    return redirect('cotizacion_detalle', pk=cotizacion_pk)


@staff_member_required
def cotizacion_cerrar(request, pk):
    cotizacion = get_object_or_404(Cotizacion, pk=pk)
    if request.method == 'POST':
        cotizacion.cerrada = True
        cotizacion.save()
    return redirect('cotizacion_detalle', pk=pk)


@staff_member_required
def cotizacion_eliminar(request, pk):
    cotizacion = get_object_or_404(Cotizacion, pk=pk)
    if request.method == 'POST':
        cotizacion.delete()
        return redirect('cotizaciones_lista')
    return render(request, 'confirmar_eliminar.html', {
        'objeto': cotizacion.descripcion,
        'cancelar_url': 'cotizaciones_lista',
    })