from django.db import models
from django.db.models import Sum
from catalogo.models import Presentacion


class PedidoApartado(models.Model):

    ESTADO_CHOICES = [
        ('abierto', 'Abierto'),
        ('liquidado', 'Liquidado'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]

    folio = models.CharField(max_length=20, unique=True, editable=False)
    cliente_nombre = models.CharField(max_length=150, verbose_name='Nombre del cliente')
    cliente_telefono = models.CharField(max_length=20, blank=True, verbose_name='Teléfono')
    cliente_ref = models.CharField(max_length=100, blank=True, verbose_name='Referencia / Red social')
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='abierto'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-fecha_creacion']

    def save(self, *args, **kwargs):
        # Generar folio automático: APT-0001, APT-0002...
        if not self.folio:
            ultimo = PedidoApartado.objects.order_by('id').last()
            siguiente = (ultimo.id + 1) if ultimo else 1
            self.folio = f'APT-{siguiente:04d}'

        super().save(*args, **kwargs)

    @property
    def total(self):
        return self.items.aggregate(
            t=Sum(
                models.F('precio_unitario') * models.F('cantidad'),
                output_field=models.DecimalField()
            )
        )['t'] or 0

    @property
    def total_pagado(self):
        return self.pagos.aggregate(t=Sum('monto'))['t'] or 0

    @property
    def saldo(self):
        return self.total - self.total_pagado

    def actualizar_estado_pago(self):
        """
        Cambia a Liquidado únicamente si los pagos registrados
        cubren o superan el total congelado del pedido.
        """
        if self.estado in ['entregado', 'cancelado']:
            return

        nuevo_estado = 'liquidado' if self.total_pagado >= self.total else 'abierto'

        if self.estado != nuevo_estado:
            self.estado = nuevo_estado
            self.save(update_fields=['estado'])

    def __str__(self):
        return f'{self.folio} — {self.cliente_nombre}'


class PedidoApartadoItem(models.Model):
    pedido = models.ForeignKey(
        PedidoApartado,
        on_delete=models.CASCADE,
        related_name='items'
    )
    presentacion = models.ForeignKey(
        Presentacion,
        on_delete=models.PROTECT,
        related_name='apartado_items'
    )
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Precio al momento'
    )

    class Meta:
        verbose_name = 'Producto del pedido'
        verbose_name_plural = 'Productos del pedido'

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad

    def __str__(self):
        return f'{self.presentacion} x{self.cantidad}'


class PagoApartado(models.Model):

    METODO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('deposito', 'Depósito'),
    ]

    pedido = models.ForeignKey(
        PedidoApartado,
        on_delete=models.CASCADE,
        related_name='pagos'
    )
    fecha = models.DateField()
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo = models.CharField(
        max_length=20,
        choices=METODO_CHOICES,
        default='efectivo'
    )
    comprobante = models.ImageField(
        upload_to='comprobantes/',
        blank=True,
        null=True
    )
    observaciones = models.TextField(blank=True)

    # Relación directa entre el pago y su ingreso en contabilidad.
    movimiento_contable = models.OneToOneField(
        'contabilidad.Movimiento',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pago_apartado'
    )

    class Meta:
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['fecha']

    def registrar_movimiento_contable(self):
        """
        Crea el ingreso de contabilidad una sola vez.

        Este método debe llamarse después de guardar el pago,
        dentro de una transacción atómica desde la vista.
        """
        # Evita crear movimientos duplicados.
        if self.movimiento_contable_id:
            return self.movimiento_contable

        # Importación local: evita una dependencia circular entre apps.
        from contabilidad.models import Concepto, Movimiento

        concepto, _ = Concepto.objects.get_or_create(
            nombre='Pago de apartado',
            defaults={
                'tipo': 'ingreso',
                'descripcion': 'Pagos recibidos de pedidos apartados.'
            }
        )

        movimiento = Movimiento.objects.create(
            fecha=self.fecha,
            concepto=concepto,
            monto=self.monto,
            cantidad=1,
            descripcion=(
                f'Pago {self.get_metodo_display().lower()} — '
                f'Pedido {self.pedido.folio} — '
                f'{self.pedido.cliente_nombre}'
            ),
            estado='confirmado'
        )

        self.movimiento_contable = movimiento
        self.save(update_fields=['movimiento_contable'])

        return movimiento

    def __str__(self):
        return f'${self.monto} — {self.fecha}'