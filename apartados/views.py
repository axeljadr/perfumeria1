from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from catalogo.models import Presentacion
from .models import PedidoApartado, PedidoApartadoItem, PagoApartado
from .forms import PedidoApartadoForm, PedidoApartadoItemFormSet, PagoApartadoForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import uuid
from django_ratelimit.decorators import ratelimit


def obtener_ip_cliente(group, request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()

    return request.META.get('REMOTE_ADDR', '')


@ratelimit(key=obtener_ip_cliente, rate='40/m', block=True)
def lista_pedidos(request):
    estado = request.GET.get('estado')
    pedidos = (
        PedidoApartado.objects
        .prefetch_related('items', 'items__presentacion', 'items__presentacion__perfume', 'pagos')
    )
    if estado:
        pedidos = pedidos.filter(estado=estado)
    return render(request, 'apartados/lista.html', {
        'pedidos': pedidos,
        'estado_actual': estado,
    })


@staff_member_required
@transaction.atomic
def crear_pedido(request):
    if request.method == 'POST':
        form = PedidoApartadoForm(request.POST)
        formset = PedidoApartadoItemFormSet(request.POST, prefix='items')
        if form.is_valid() and formset.is_valid():
            pedido = form.save()  # ← guarda primero el pedido (genera folio + token + QR)

            # ← ahora sí asigna el pedido al formset y guarda
            formset.instance = pedido
            items = formset.save(commit=False)
            for item in items:
                item.pedido = pedido
                if not item.precio_unitario:
                    item.precio_unitario = item.presentacion.precio
                item.save()
            for deleted in formset.deleted_objects:
                deleted.delete()

            # Regenerar el QR ahora que los ítems ya existen
            # (el modelo lo genera en save(), pero aquí lo forzamos
            # por si la URL pública necesita estar ya guardada).
            if not pedido.codigo_qr:
                pedido.generar_codigo_qr()
                pedido.save(update_fields=['codigo_qr'])

            messages.success(request, f'Pedido {pedido.folio} creado correctamente.')
            return redirect('apartados:detalle', pk=pedido.pk)
    else:
        form = PedidoApartadoForm()
        formset = PedidoApartadoItemFormSet(
            prefix='items',
            queryset=PedidoApartadoItem.objects.none()
        )

    presentaciones = Presentacion.objects.filter(activo=True).select_related('perfume')
    return render(request, 'apartados/crear.html', {
        'form': form,
        'formset': formset,
        'presentaciones': presentaciones,
    })


def detalle_pedido(request, pk):
    pedido = get_object_or_404(
        PedidoApartado.objects.prefetch_related(
            'items', 'items__presentacion', 'items__presentacion__perfume', 'pagos'
        ),
        pk=pk
    )
    return render(request, 'apartados/detalle.html', {
        'pedido': pedido,
    })


@staff_member_required
@transaction.atomic
def registrar_pago(request, pk):
    pedido = get_object_or_404(PedidoApartado, pk=pk)
    if pedido.estado in ['entregado', 'cancelado']:
        messages.error(request, 'No se pueden registrar pagos en pedidos entregados o cancelados.')
        return redirect('apartados:detalle', pk=pk)

    if request.method == 'POST':
        form = PagoApartadoForm(request.POST, request.FILES)
        if form.is_valid():
            pago = form.save(commit=False)
            pago.pedido = pedido
            pago.save()
            pago.registrar_movimiento_contable()
            pedido.actualizar_estado_pago()
            if pedido.saldo <= 0:
                pedido.estado = 'liquidado'
                pedido.save()
                messages.success(request, 'Pago registrado. El pedido está liquidado.')
            else:
                messages.success(request, 'Pago registrado.')
            return redirect('apartados:detalle', pk=pk)
    else:
        form = PagoApartadoForm()

    return render(request, 'apartados/registrar_pago.html', {
        'form': form,
        'pedido': pedido,
    })


@staff_member_required
def cambiar_estado(request, pk):
    pedido = get_object_or_404(PedidoApartado, pk=pk)

    if request.method != 'POST':
        return redirect('apartados:detalle', pk=pedido.pk)

    nuevo_estado = request.POST.get('estado')
    regenerar_qr = request.POST.get('regenerar_qr') == '1'

    # Permite regenerar el QR sin modificar el estado del pedido.
    if regenerar_qr:
        pedido.generar_codigo_qr()
        pedido.save(update_fields=['codigo_qr'])

        messages.success(
            request,
            f'Código QR del pedido {pedido.folio} generado correctamente.'
        )
        return redirect('apartados:detalle', pk=pedido.pk)

    estados_validos = dict(PedidoApartado.ESTADO_CHOICES)

    if nuevo_estado not in estados_validos:
        messages.error(request, 'El estado seleccionado no es válido.')
        return redirect('apartados:detalle', pk=pedido.pk)

    pedido.estado = nuevo_estado

    # Al entregar, se crea un QR si todavía no existe.
    if nuevo_estado == 'entregado' and not pedido.codigo_qr:
        pedido.generar_codigo_qr()
        pedido.save(update_fields=['estado', 'codigo_qr'])
    else:
        pedido.save(update_fields=['estado'])

    messages.success(
        request,
        f'Pedido {pedido.folio} actualizado a: {pedido.get_estado_display()}.'
    )

    return redirect('apartados:detalle', pk=pedido.pk)


@staff_member_required
def eliminar_pago(request, pk):
    pago = get_object_or_404(PagoApartado, pk=pk)
    pedido_pk = pago.pedido.pk
    pago.delete()
    messages.success(request, 'Pago eliminado correctamente.')
    return redirect('apartados:detalle', pk=pedido_pk)


@staff_member_required
def buscar_presentaciones(request):
    termino = request.GET.get('q', '').strip()

    presentaciones = (
        Presentacion.objects
        .filter(activo=True)
        .select_related('perfume')
    )

    if termino:
        presentaciones = presentaciones.filter(
            perfume__nombre__icontains=termino
        ) | presentaciones.filter(
            perfume__marca__icontains=termino
        )

    presentaciones = presentaciones.order_by(
        'perfume__marca',
        'perfume__nombre',
        'volumen_ml',
    )[:15]

    resultados = []

    for presentacion in presentaciones:
        resultados.append({
            'id': presentacion.id,
            'nombre': (
                f'{presentacion.perfume.marca} — '
                f'{presentacion.perfume.nombre} · '
                f'{presentacion.get_tipo_display()} '
                f'{presentacion.volumen_ml} ml'
            ),
            'precio': str(presentacion.precio),
            'stock': presentacion.stock,
        })

    return JsonResponse(resultados, safe=False)



@login_required
@transaction.atomic
def liquidar_pedido(request, pk):
    """
    Registra un pago por el saldo restante del pedido
    y lo contabiliza automáticamente.
    Solo acepta POST para evitar liquidaciones accidentales.
    """
    pedido = get_object_or_404(PedidoApartado, pk=pk)

    if request.method != 'POST':
        return redirect('apartados:detalle_pedido', pk=pk)

    saldo = pedido.saldo

    if saldo <= 0:
        messages.warning(request, 'Este pedido ya no tiene saldo pendiente.')
        return redirect('apartados:detalle_pedido', pk=pk)

    if pedido.estado in ['entregado', 'cancelado']:
        messages.error(request, 'No se puede liquidar un pedido entregado o cancelado.')
        return redirect('apartados:detalle_pedido', pk=pk)

    # Crea el pago por el saldo restante
    metodo = request.POST.get('metodo', 'efectivo')
    pago = PagoApartado.objects.create(
        pedido=pedido,
        fecha=timezone.now().date(),
        monto=saldo,
        metodo=metodo,
        observaciones='Liquidación total del saldo pendiente.'
    )

    # Registra en contabilidad y actualiza estado
    pago.registrar_movimiento_contable()
    pedido.actualizar_estado_pago()

    messages.success(
        request,
        f'Pedido {pedido.folio} liquidado correctamente. '
        f'Se registró un pago de ${saldo} por {pago.get_metodo_display().lower()}.'
    )
    return redirect('apartados:detalle', pk=pk)


@ratelimit(key=obtener_ip_cliente, rate='40/m', block=True)
def pedido_publico(request, token):
    pedido = get_object_or_404(
        PedidoApartado.objects.prefetch_related(
    'items',
    'items__presentacion',
    'items__presentacion__perfume',
    'items__presentacion__perfume__acordes',
    'items__presentacion__perfume__notas',
    'items__presentacion__perfume__familia_olfativa',
    ),
        token_publico=token,
    )

    return render(
        request,
        'apartados/pedido_publico.html',
        {'pedido': pedido},
    )

@staff_member_required
def eliminar_pedido(request, pk):
    """
    Elimina un pedido duplicado o creado por error.
    Solo permite eliminar si no tiene ningún pago registrado
    (saldo == total, es decir total_pagado == 0).
    """
    pedido = get_object_or_404(PedidoApartado, pk=pk)

    if pedido.total_pagado > 0:
        messages.error(
            request,
            'No se puede eliminar este pedido porque ya tiene pagos registrados.'
        )
        return redirect('apartados:detalle', pk=pedido.pk)

    if request.method == 'POST':
        folio = pedido.folio
        pedido.delete()
        messages.success(request, f'Pedido {folio} eliminado correctamente.')
        return redirect('apartados:lista_pedidos')

    return redirect('apartados:detalle', pk=pedido.pk)

from datetime import date, timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum, F, DecimalField
from django.shortcuts import render
from django.utils import timezone

from .models import PedidoApartado, PedidoApartadoItem


def _parse_fecha(valor, default):
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError):
        return default


@staff_member_required
def presentaciones_mas_vendidas(request):
    hoy = timezone.localdate()
    fecha_fin = _parse_fecha(request.GET.get("fecha_fin"), hoy)
    fecha_inicio = _parse_fecha(
        request.GET.get("fecha_inicio"), hoy - timedelta(days=30)
    )
    tipo = request.GET.get("tipo", "")
    incluir_abiertos = request.GET.get("incluir_abiertos") == "1"

    items = PedidoApartadoItem.objects.filter(
        pedido__fecha_creacion__date__range=(fecha_inicio, fecha_fin),
    ).exclude(pedido__estado="cancelado")

    # Por defecto solo cuenta pedidos con venta real (liquidado / entregado)
    if not incluir_abiertos:
        items = items.filter(pedido__estado__in=["liquidado", "entregado"])

    if tipo:
        items = items.filter(presentacion__tipo=tipo)

    ranking = (
        items.values(
            "presentacion_id",
            "presentacion__perfume__marca",
            "presentacion__perfume__nombre",
            "presentacion__tipo",
            "presentacion__volumen_ml",
        )
        .annotate(
            veces_en_pedidos=Count("pedido", distinct=True),
            unidades=Sum("cantidad"),
            ingresos=Sum(
                F("cantidad") * F("precio_unitario"),
                output_field=DecimalField(),
            ),
        )
        .order_by("-unidades", "-veces_en_pedidos")
    )

    return render(
        request,
        "apartados/mas_vendidas.html",
        {
            "ranking": ranking,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "tipo": tipo,
            "incluir_abiertos": incluir_abiertos,
            "tipos": [
                ("decant", "Decant"),
                ("original", "Tamaño Original"),
                ("set", "Set"),
                ("miniatura", "Miniatura"),
                ("otro", "Otro"),
            ],
        },
    )


@staff_member_required
def reporte_semanal(request):
    hoy = timezone.localdate()
    referencia = _parse_fecha(request.GET.get("fecha"), hoy)
    lunes = referencia - timedelta(days=referencia.weekday())
    domingo = lunes + timedelta(days=6)

    pedidos = (
        PedidoApartado.objects.filter(fecha_creacion__date__range=(lunes, domingo))
        .exclude(estado="cancelado")
        .prefetch_related("items__presentacion__perfume", "pagos")
        .order_by("fecha_creacion")
    )

    total_semana = 0
    pagado_semana = 0
    for p in pedidos:
        items = list(p.items.all())  # usa el prefetch, sin queries extra
        p.total_calc = sum(i.precio_unitario * i.cantidad for i in items)
        p.pagado_calc = sum(pg.monto for pg in p.pagos.all())
        p.saldo_calc = p.total_calc - p.pagado_calc
        total_semana += p.total_calc
        pagado_semana += p.pagado_calc

    resumen = (
        PedidoApartadoItem.objects.filter(pedido__in=pedidos)
        .values(
            "presentacion__perfume__marca",
            "presentacion__perfume__nombre",
            "presentacion__tipo",
            "presentacion__volumen_ml",
        )
        .annotate(unidades=Sum("cantidad"), pedidos=Count("pedido", distinct=True))
        .order_by("-unidades")
    )

    return render(
        request,
        "apartados/reporte_semanal.html",
        {
            "pedidos": pedidos,
            "resumen": resumen,
            "lunes": lunes,
            "domingo": domingo,
            "semana_anterior": lunes - timedelta(days=7),
            "semana_siguiente": lunes + timedelta(days=7),
            "total_semana": total_semana,
            "pagado_semana": pagado_semana,
            "saldo_semana": total_semana - pagado_semana,
        },
    )