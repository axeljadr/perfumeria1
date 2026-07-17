from django.shortcuts import render, redirect, get_object_or_404 
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.utils import timezone
from django.http import JsonResponse
from decimal import Decimal
from datetime import datetime, timedelta

from .models import (
    Compra, Presentacion, Movimiento, Concepto, 
    ConfiguracionDecant, Perfume
)
from .forms import (
    CompraForm, CompraProcesarForm, PresentacionForm, 
    PresentacionBatchForm, MovimientoForm, MovimientoFiltroForm,
    ConfiguracionDecantForm, ReporteForm
)
from .utils import get_balance, get_resumen_mensual


# ============================================================
# DASHBOARD PRINCIPAL
# ============================================================

@login_required
def dashboard(request):
    """Dashboard principal de gestión"""
    # Balance general
    balance = get_balance()
    resumen_mes = get_resumen_mensual()
    
    # Últimos movimientos
    ultimos_movimientos = Movimiento.objects.filter(
        estado='confirmado'
    ).select_related('concepto')[:10]
    
    # Últimas compras
    ultimas_compras = Compra.objects.filter(
        estado='completada'
    ).select_related('perfume')[:5]
    
    # Compras pendientes
    compras_pendientes = Compra.objects.filter(
        estado='en_proceso'
    ).count()
    
    # Stock bajo (presentaciones con stock < 5)
    stock_bajo = Presentacion.objects.filter(
        stock__lt=5,
        activo=True
    ).select_related('perfume')[:10]
    
    # Totales
    total_perfumes = Perfume.objects.filter(activo=True).count()
    total_presentaciones = Presentacion.objects.filter(activo=True).count()
    
    context = {
        'balance': balance,
        'resumen_mes': resumen_mes,
        'ultimos_movimientos': ultimos_movimientos,
        'ultimas_compras': ultimas_compras,
        'compras_pendientes': compras_pendientes,
        'stock_bajo': stock_bajo,
        'total_perfumes': total_perfumes,
        'total_presentaciones': total_presentaciones,
    }
    
    return render(request, 'contabilidad/dashboard.html', context)


# ============================================================
# VISTAS DE COMPRAS
# ============================================================

@login_required
def compra_list(request):
    """Lista de compras con filtros"""
    compras = Compra.objects.select_related('perfume', 'movimiento_contable').all()
    
    # Filtros
    estado = request.GET.get('estado')
    if estado:
        compras = compras.filter(estado=estado)
    
    perfume_id = request.GET.get('perfume')
    if perfume_id:
        compras = compras.filter(perfume_id=perfume_id)
    
    fecha_inicio = request.GET.get('fecha_inicio')
    if fecha_inicio:
        compras = compras.filter(fecha_compra__gte=fecha_inicio)
    
    fecha_fin = request.GET.get('fecha_fin')
    if fecha_fin:
        compras = compras.filter(fecha_compra__lte=fecha_fin)
    
    context = {
        'compras': compras,
        'perfumes': Perfume.objects.filter(activo=True),
        'total_compras': compras.count(),
        'total_invertido': compras.aggregate(Sum('costo_total'))['costo_total__sum'] or 0,
    }
    
    return render(request, 'contabilidad/compras/compra_list.html', context)


@login_required
def compra_create(request):
    """Crear una nueva compra"""
    if request.method == 'POST':
        form = CompraForm(request.POST)
        if form.is_valid():
            compra = form.save(commit=False)
            # Calcular costo total
            compra.costo_total = compra.cantidad_comprada * compra.precio_unitario
            compra.save()
            messages.success(request, f'✅ Compra creada exitosamente. ID: #{compra.id}')
            return redirect('contabilidad:compra_detail', pk=compra.pk)
    else:
        form = CompraForm()
    
    return render(request, 'contabilidad/compras/compra_form.html', {'form': form, 'action': 'crear'})


@login_required
def compra_detail(request, pk):
    """Detalle de una compra"""
    compra = get_object_or_404(Compra, pk=pk)
    
    # Precios calculados (para mostrar)
    precios_decants = None
    if compra.estado != 'completada':
        try:
            precios_decants = compra.calcular_precios_decants()
        except:
            precios_decants = {}
    
    # Presentaciones del perfume
    presentaciones = compra.perfume.presentaciones.filter(activo=True)
    
    context = {
        'compra': compra,
        'precios_decants': precios_decants,
        'presentaciones': presentaciones,
        'puede_procesar': compra.estado == 'en_proceso',
    }
    
    return render(request, 'contabilidad/compras/compra_detail.html', context)


@login_required
def compra_procesar(request, pk):
    """Procesar una compra (confirmar y actualizar inventario)"""
    compra = get_object_or_404(Compra, pk=pk)
    
    if compra.estado == 'completada':
        messages.warning(request, '⚠️ Esta compra ya fue procesada')
        return redirect('contabilidad:compra_detail', pk=pk)
    
    if request.method == 'POST':
        form = CompraProcesarForm(request.POST)
        if form.is_valid():
            try:
                compra.procesar_compra()
                messages.success(request, f'✅ Compra #{compra.id} procesada exitosamente')
                return redirect('contabilidad:compra_detail', pk=compra.pk)
            except Exception as e:
                messages.error(request, f'❌ Error al procesar: {str(e)}')
    else:
        form = CompraProcesarForm()
    
    context = {
        'compra': compra,
        'form': form,
    }
    
    return render(request, 'contabilidad/compras/compra_procesar.html', context)


@login_required
def compra_delete(request, pk):
    """Eliminar una compra (solo si está en proceso)"""
    compra = get_object_or_404(Compra, pk=pk)
    
    if compra.estado == 'completada':
        messages.error(request, '❌ No se puede eliminar una compra completada')
        return redirect('contabilidad:compra_detail', pk=pk)
    
    if request.method == 'POST':
        compra.delete()
        messages.success(request, '✅ Compra eliminada exitosamente')
        return redirect('contabilidad:compra_list')
    
    return render(request, 'confirmar_eliminar.html', {'compra': compra})


# ============================================================
# VISTAS DE PRESENTACIONES
# ============================================================

@login_required
def presentacion_list(request):
    """Lista de presentaciones con filtros"""
    presentaciones = Presentacion.objects.select_related('perfume').filter(activo=True)
    
    perfume_id = request.GET.get('perfume')
    if perfume_id:
        presentaciones = presentaciones.filter(perfume_id=perfume_id)
    
    tipo = request.GET.get('tipo')
    if tipo:
        presentaciones = presentaciones.filter(tipo=tipo)
    
    context = {
        'presentaciones': presentaciones,
        'perfumes': Perfume.objects.filter(activo=True),
        'total_stock': presentaciones.aggregate(Sum('stock'))['stock__sum'] or 0, 
    }
    
    return render(request, 'contabilidad/presentaciones/presentacion_list.html', context)


@login_required
def presentacion_update(request, pk):
    """Actualizar una presentación"""
    presentacion = get_object_or_404(Presentacion, pk=pk)
    
    if request.method == 'POST':
        form = PresentacionForm(request.POST, instance=presentacion)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Presentación actualizada exitosamente')
            return redirect('contabilidad:presentacion_list')
    else:
        form = PresentacionForm(instance=presentacion)
    
    return render(request, 'contabilidad/presentaciones/presentacion_form.html', {
        'form': form,
        'presentacion': presentacion,
        'action': 'editar'
    })


@login_required
def presentacion_batch_create(request):
    """Crear múltiples presentaciones a la vez"""
    if request.method == 'POST':
        form = PresentacionBatchForm(request.POST)
        if form.is_valid():
            perfume = form.cleaned_data['perfume']
            precios = form.cleaned_data['precios']
            stock_inicial = form.cleaned_data.get('stock_inicial', 0)
            
            creadas = 0
            for ml, precio in precios.items():
                tipo = 'original' if ml == 100 else 'decant'
                presentacion, created = Presentacion.objects.get_or_create(
                    perfume=perfume,
                    tipo=tipo,
                    volumen_ml=str(ml),
                    defaults={
                        'precio': precio,
                        'stock': stock_inicial,
                        'activo': True,
                        'precio_automatico': False
                    }
                )
                if created:
                    creadas += 1
            
            messages.success(request, f'✅ {creadas} presentaciones creadas exitosamente')
            return redirect('contabilidad:presentacion_list')
    else:
        form = PresentacionBatchForm()
    
    return render(request, 'contabilidad/presentaciones/presentacion_batch.html', {'form': form})


# ============================================================
# VISTAS DE MOVIMIENTOS CONTABLES
# ============================================================

@login_required
def movimiento_list(request):
    """Lista de movimientos contables con filtros"""
    movimientos = Movimiento.objects.select_related('concepto').all()
    
    # Filtros
    filtro_form = MovimientoFiltroForm(request.GET)
    if filtro_form.is_valid():
        fecha_inicio = filtro_form.cleaned_data.get('fecha_inicio')
        if fecha_inicio:
            movimientos = movimientos.filter(fecha__gte=fecha_inicio)
        
        fecha_fin = filtro_form.cleaned_data.get('fecha_fin')
        if fecha_fin:
            movimientos = movimientos.filter(fecha__lte=fecha_fin)
        
        concepto = filtro_form.cleaned_data.get('concepto')
        if concepto:
            movimientos = movimientos.filter(concepto=concepto)
        
        tipo = filtro_form.cleaned_data.get('tipo')
        if tipo:
            movimientos = movimientos.filter(concepto__tipo=tipo)
        
        estado = filtro_form.cleaned_data.get('estado')
        if estado:
            movimientos = movimientos.filter(estado=estado)
    
    # Totales
    total_ingresos = movimientos.filter(concepto__tipo='ingreso', estado='confirmado').aggregate(Sum('monto'))['monto__sum'] or 0
    total_egresos = movimientos.filter(concepto__tipo='egreso', estado='confirmado').aggregate(Sum('monto'))['monto__sum'] or 0
    
    context = {
        'movimientos': movimientos,
        'filtro_form': filtro_form,
        'total_ingresos': total_ingresos,
        'total_egresos': total_egresos,
        'balance': total_ingresos - total_egresos,
    }
    
    return render(request, 'contabilidad/movimientos/movimiento_list.html', context)


@login_required
def movimiento_create(request):
    """Crear un nuevo movimiento contable"""
    if request.method == 'POST':
        form = MovimientoForm(request.POST)
        if form.is_valid():
            movimiento = form.save()
            messages.success(request, f'✅ Movimiento creado: {movimiento}')
            return redirect('contabilidad:movimiento_list')
    else:
        form = MovimientoForm()
    
    return render(request, 'contabilidad/movimientos/movimiento_form.html', {'form': form, 'action': 'crear'})


@login_required
def movimiento_update(request, pk):
    """Actualizar un movimiento contable"""
    movimiento = get_object_or_404(Movimiento, pk=pk)
    
    if movimiento.estado == 'confirmado':
        messages.warning(request, '⚠️ No se puede editar un movimiento confirmado')
        return redirect('contabilidad:movimiento_list')
    
    if request.method == 'POST':
        form = MovimientoForm(request.POST, instance=movimiento)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Movimiento actualizado')
            return redirect('contabilidad:movimiento_list')
    else:
        form = MovimientoForm(instance=movimiento)
    
    return render(request, 'contabilidad/movimientos/movimiento_form.html', {
        'form': form,
        'movimiento': movimiento,
        'action': 'editar'
    })


@login_required
def movimiento_delete(request, pk):
    """Eliminar un movimiento contable"""
    movimiento = get_object_or_404(Movimiento, pk=pk)
    
    if movimiento.estado == 'confirmado':
        messages.error(request, '❌ No se puede eliminar un movimiento confirmado')
        return redirect('contabilidad:movimiento_list')
    
    if request.method == 'POST':
        movimiento.delete()
        messages.success(request, '✅ Movimiento eliminado')
        return redirect('contabilidad:movimiento_list')
    
    return render(request, 'contabilidad/movimiento_confirm_delete.html', {'movimiento': movimiento})


# ============================================================
# VISTAS DE CONFIGURACIÓN
# ============================================================

@login_required
def configuracion_edit(request):
    """Editar configuración de decants"""
    config = ConfiguracionDecant.get_config()
    
    if request.method == 'POST':
        form = ConfiguracionDecantForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Configuración actualizada exitosamente')
            return redirect('contabilidad:dashboard')
    else:
        form = ConfiguracionDecantForm(instance=config)
    
    return render(request, 'contabilidad/configuracion_form.html', {'form': form})




@login_required
def reportes(request):
    """Generación de reportes"""
    hoy = timezone.now().date()
    
    # Si hay parámetros GET, mostrar el reporte directamente (reportes rápidos)
    if request.GET.get('tipo'):
        return generar_reporte(request.GET)
    
    if request.method == 'POST':
        form = ReporteForm(request.POST)
        if form.is_valid():
            tipo_reporte = form.cleaned_data['tipo_reporte']
            formato = form.cleaned_data['formato']
            fecha_inicio = form.cleaned_data['fecha_inicio']
            fecha_fin = form.cleaned_data['fecha_fin']
            
            # Si es HTML, mostrar en la misma página
            if formato == 'html':
                params = {
                    'tipo': tipo_reporte,
                    'inicio': fecha_inicio.strftime('%Y-%m-%d'),
                    'fin': fecha_fin.strftime('%Y-%m-%d'),
                }
                return generar_reporte(params)
            else:
                # Para PDF o Excel, redirigir a otra vista (pendiente de implementar)
                messages.info(request, f'Formato {formato} en desarrollo')
                return redirect('contabilidad:reportes')
    else:
        form = ReporteForm(initial={
            'fecha_inicio': hoy.replace(day=1),
            'fecha_fin': hoy
        })
    
    context = {
        'form': form,
        'hoy': hoy,
    }
    
    return render(request, 'contabilidad/reportes/reportes.html', context)


def generar_reporte(params):
    """Genera el reporte según los parámetros"""
    tipo = params.get('tipo')
    fecha_inicio = params.get('inicio')
    fecha_fin = params.get('fin')
    
    # Convertir fechas
    try:
        fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        hoy = timezone.now().date()
        fecha_inicio = hoy.replace(day=1)
        fecha_fin = hoy
    
    context = {
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'hoy': timezone.now().date(),
        'tipo_reporte': tipo,
    }
    
    if tipo == 'compras':
        compras = Compra.objects.filter(
            fecha_compra__range=[fecha_inicio, fecha_fin]
        ).select_related('perfume')
        
        context.update({
            'titulo': 'Reporte de Compras',
            'datos': compras,
            'totales': {
                'cantidad': compras.count(),
                'total': compras.aggregate(Sum('costo_total'))['costo_total__sum'] or 0,
            }
        })
        template = 'contabilidad/reportes/reporte_resultado.html'
    
    elif tipo == 'movimientos':
        movimientos = Movimiento.objects.filter(
            fecha__range=[fecha_inicio, fecha_fin],
            estado='confirmado'
        ).select_related('concepto')
        
        ingresos = movimientos.filter(concepto__tipo='ingreso').aggregate(Sum('monto'))['monto__sum'] or 0
        egresos = movimientos.filter(concepto__tipo='egreso').aggregate(Sum('monto'))['monto__sum'] or 0
        
        context.update({
            'titulo': 'Reporte de Movimientos',
            'datos': movimientos,
            'totales': {
                'ingresos': ingresos,
                'egresos': egresos,
                'balance': ingresos - egresos,
            }
        })
        template = 'contabilidad/reportes/reporte_resultado.html'
    
    elif tipo == 'inventario':
        presentaciones = Presentacion.objects.filter(activo=True).select_related('perfume')
        stock_bajo = presentaciones.filter(stock__lt=5)
        
        context.update({
            'titulo': 'Reporte de Inventario',
            'datos': presentaciones,
            'stock_bajo': stock_bajo,
            'totales': {
                'stock_total': presentaciones.aggregate(Sum('stock'))['stock__sum'] or 0,
                'valor_total': 0,  # Calcular según tu lógica
            }
        })
        template = 'contabilidad/reportes/reporte_resultado.html'
    
    elif tipo == 'utilidades':
        movimientos = Movimiento.objects.filter(
            fecha__range=[fecha_inicio, fecha_fin],
            estado='confirmado'
        ).select_related('concepto')
        
        ingresos = movimientos.filter(concepto__tipo='ingreso')
        egresos = movimientos.filter(concepto__tipo='egreso')
        
        ingresos_por_concepto = ingresos.values('concepto__nombre').annotate(total=Sum('monto'))
        egresos_por_concepto = egresos.values('concepto__nombre').annotate(total=Sum('monto'))
        
        total_ingresos = ingresos.aggregate(Sum('monto'))['monto__sum'] or 0
        total_egresos = egresos.aggregate(Sum('monto'))['monto__sum'] or 0
        
        context.update({
            'titulo': 'Reporte de Utilidades',
            'datos': movimientos,
            'ingresos_por_concepto': ingresos_por_concepto,
            'egresos_por_concepto': egresos_por_concepto,
            'totales': {
                'ingresos': total_ingresos,
                'egresos': total_egresos,
                'utilidad': total_ingresos - total_egresos,
            }
        })
        template = 'contabilidad/reportes/reporte_resultado.html'
    
    else:
        context.update({
            'titulo': 'Reporte',
            'datos': []
        })
        template = 'contabilidad/reportes/reporte_resultado.html'
    
    return render(request, template, context)