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

def pedido_publico(request, token):
    """
    Vista pública: accesible sin login mediante el token UUID del QR.
    Muestra solo la información del pedido relevante para el cliente.
    """
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