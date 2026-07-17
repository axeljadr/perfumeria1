from django.db.models import Sum
from datetime import datetime
from .models import Movimiento, Concepto


def get_balance(fecha_inicio=None, fecha_fin=None):
    """Calcula el balance en un período"""
    queryset = Movimiento.objects.filter(estado='confirmado')
    
    if fecha_inicio:
        queryset = queryset.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        queryset = queryset.filter(fecha__lte=fecha_fin)
    
    ingresos = queryset.filter(concepto__tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
    egresos = queryset.filter(concepto__tipo='egreso').aggregate(total=Sum('monto'))['total'] or 0
    
    return {
        'ingresos': ingresos,
        'egresos': egresos,
        'balance': ingresos - egresos
    }


def get_resumen_mensual(mes=None, anio=None):
    """Resumen del mes actual"""
    if not mes:
        mes = datetime.now().month
    if not anio:
        anio = datetime.now().year
    
    movimientos = Movimiento.objects.filter(
        fecha__year=anio,
        fecha__month=mes,
        estado='confirmado'
    )
    
    total_ingresos = movimientos.filter(concepto__tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
    total_egresos = movimientos.filter(concepto__tipo='egreso').aggregate(total=Sum('monto'))['total'] or 0
    
    ingresos_por_concepto = movimientos.filter(concepto__tipo='ingreso').values(
        'concepto__nombre'
    ).annotate(total=Sum('monto'))
    
    egresos_por_concepto = movimientos.filter(concepto__tipo='egreso').values(
        'concepto__nombre'
    ).annotate(total=Sum('monto'))
    
    return {
        'total_ingresos': total_ingresos,
        'total_egresos': total_egresos,
        'balance': total_ingresos - total_egresos,
        'ingresos_por_concepto': ingresos_por_concepto,
        'egresos_por_concepto': egresos_por_concepto,
    }


def calcular_utilidad_potencial(perfume):
    """Calcula la utilidad potencial de un perfume basado en stock"""
    total_ingresos = 0
    for presentacion in perfume.presentaciones.filter(activo=True):
        total_ingresos += presentacion.precio * presentacion.stock
    
    # Asumiendo que el perfume tiene precio_compra
    if hasattr(perfume, 'precio_compra'):
        inversion = perfume.precio_compra
    else:
        inversion = 0
    
    return {
        'ingresos_potenciales': total_ingresos,
        'inversion': inversion,
        'utilidad_potencial': total_ingresos - inversion
    }