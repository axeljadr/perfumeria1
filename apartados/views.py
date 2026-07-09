from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db import transaction
from catalogo.models import Presentacion
from .models import PedidoApartado, PedidoApartadoItem, PagoApartado
from .forms import PedidoApartadoForm, PedidoApartadoItemFormSet, PagoApartadoForm


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
            pedido = form.save()  # ← guarda primero el pedido

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
    if request.method == 'POST':
        nuevo = request.POST.get('estado')
        if nuevo in dict(PedidoApartado.ESTADO_CHOICES):
            pedido.estado = nuevo
            pedido.save()
            messages.success(request, f'Estado actualizado a {pedido.get_estado_display()}.')
    return redirect('apartados:detalle', pk=pk)


@staff_member_required
def eliminar_pago(request, pk):
    pago = get_object_or_404(PagoApartado, pk=pk)
    pedido_pk = pago.pedido.pk
    pago.delete()
    messages.success(request, 'Pago eliminado correctamente.')
    return redirect('apartados:detalle', pk=pedido_pk)