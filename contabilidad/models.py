from django.db import models
from django.utils import timezone
from decimal import Decimal
import math
from django.db import models, transaction
from catalogo.models import Perfume, Presentacion



# ========== TABLA 1: INVENTARIO ==========
class Inventario(models.Model):
    UNIDAD_CHOICES = [
        ('unidad', 'Unidad'),
        ('ml', 'Mililitro'),
    ]
    
    nombre = models.CharField(max_length=100, unique=True)
    cantidad = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unidad = models.CharField(max_length=20, choices=UNIDAD_CHOICES, default='unidad')
    descripcion = models.TextField(blank=True, null=True)
    stock_minimo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "inventario"
        verbose_name_plural = "inventarios"
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.nombre} - {self.cantidad} {self.get_unidad_display()}"



class ConfiguracionDecant(models.Model):
    bolsa_costo = models.DecimalField(max_digits=10, decimal_places=2, default=10.00)
    jeringa_costo = models.DecimalField(max_digits=10, decimal_places=2, default=5.00)
    porcentaje_ganancia = models.DecimalField(max_digits=5, decimal_places=2, default=25.00)  # 25%
    redondeo_terminacion = models.CharField(max_length=1, default='5')  # '5' o '0'
    
    class Meta:
        verbose_name = "Configuración de Decants"
        verbose_name_plural = "Configuración de Decants"
    
    def __str__(self):
        return f"Configuración: Bolsa ${self.bolsa_costo}, Jeringa ${self.jeringa_costo}, {self.porcentaje_ganancia}%"
    
    def save(self, *args, **kwargs):
        """Asegura que solo exista un registro"""
        if not self.pk and ConfiguracionDecant.objects.exists():
            raise ValueError("Ya existe una configuración. Edita la existente.")
        super().save(*args, **kwargs)
    
    @classmethod
    def get_config(cls):
        """Obtiene la configuración o crea una por defecto"""
        config = cls.objects.first()
        if not config:
            config = cls.objects.create(
                bolsa_costo=10.00,
                jeringa_costo=5.00,
                porcentaje_ganancia=25.00,
                redondeo_terminacion='5',
            )
        return config



# ============================================================
# 3. COMPRAS (referencia a tu Perfume)
# ============================================================

class Compra(models.Model):
    ESTADO_CHOICES = [
        ('en_proceso', 'En Proceso'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
    ]
    
    perfume = models.ForeignKey(
        Perfume,  # ← Tu modelo de catalogo
        on_delete=models.PROTECT, 
        related_name='compras'
    )
    proveedor = models.CharField(max_length=200, blank=True, null=True)
    cantidad_comprada = models.PositiveIntegerField(
        help_text="Número de perfumes completos comprados"
    )
    precio_unitario = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Precio de compra por unidad"
    )
    costo_total = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Costo total de la compra"
    )
    fecha_compra = models.DateField(default=timezone.now)
    estado = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES, 
        default='en_proceso'
    )
    notas = models.TextField(blank=True, null=True)
    
    # Relación con contabilidad
    movimiento_contable = models.ForeignKey(
        'Movimiento', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='compras_asociadas'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "compra"
        verbose_name_plural = "compras"
        ordering = ["-fecha_compra"]
    
    def __str__(self):
        return f"Compra #{self.id} - {self.perfume.nombre} - {self.cantidad_comprada} unidades"
    
    def _redondear_precio(self, precio):
        config = ConfiguracionDecant.get_config()
        if config.redondeo_terminacion == '5':
            return math.ceil(precio / 5) * 5
        else:
            return math.ceil(precio / 10) * 10
    
    def calcular_precios_decants(self):
        """Calcula los precios automáticamente usando la configuración global"""
        config = ConfiguracionDecant.get_config()
        
        # Usar el precio_venta_completo de tu modelo Perfume
        # Asumiendo que tu modelo tiene este campo
        if hasattr(self.perfume, 'precio_venta_completo'):
            precio_ml = self.perfume.precio_venta_completo / 100
        else:
            # Fallback: si no tiene el campo, usa el precio de la presentación original
            original = self.perfume.presentaciones.filter(tipo='original', volumen_ml='100').first()
            if original:
                precio_ml = original.precio / 100
            else:
                raise ValueError("No se puede calcular precio por ml")
        
        insumos = config.bolsa_costo + config.jeringa_costo
        porcentaje = config.porcentaje_ganancia / 100
        
        precios = {}
        for ml in [3, 5, 10]:
            costo_base = (precio_ml * ml) + insumos
            precio_final = costo_base * (1 + porcentaje)
            precio_redondeado = self._redondear_precio(precio_final)
            precios[ml] = precio_redondeado
        
        return precios
    
    def procesar_compra(self):
        if self.estado == 'completada':
            raise ValueError('Esta compra ya fue procesada.')
        if self.estado == 'cancelada':
            raise ValueError('No se puede procesar una compra cancelada.')

        with transaction.atomic():
            concepto, _ = Concepto.objects.get_or_create(
                nombre='Compra de perfume',
                defaults={
                    'tipo': 'egreso',
                    'descripcion': 'Adquisición de perfumes para inventario',
                }
            )

            movimiento = Movimiento.objects.create(
                concepto=concepto,
                monto=self.costo_total,
                descripcion=(
                    f'Compra #{self.id} - '
                    f'{self.perfume.marca} - {self.perfume.nombre}'
                ),
                fecha=self.fecha_compra,
            )

            self.movimiento_contable = movimiento
            self.estado = 'completada'
            self.save(update_fields=['movimiento_contable', 'estado'])

        return movimiento


# ============================================================
# 4. CONTABILIDAD (Conceptos y Movimientos)
# ============================================================

class Concepto(models.Model):
    TIPO_CHOICES = [
        ('ingreso', 'Ingreso'),
        ('egreso', 'Egreso'),
    ]
    
    nombre = models.CharField(max_length=100, unique=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        verbose_name = "concepto"
        verbose_name_plural = "conceptos"
        ordering = ['tipo', 'nombre']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.nombre}"


class Movimiento(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('confirmado', 'Confirmado'),
        ('cancelado', 'Cancelado'),
    ]
    
    fecha = models.DateField(default=timezone.now)
    concepto = models.ForeignKey(
        Concepto, 
        on_delete=models.PROTECT, 
        related_name="movimientos"
    )
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    cantidad = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    estado = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES, 
        default='confirmado'
    )
    
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "movimiento"
        verbose_name_plural = "movimientos"
        ordering = ["-fecha", "-created_at"]
        indexes = [
            models.Index(fields=['fecha']),
            models.Index(fields=['concepto', 'estado']),
        ]
    
    def __str__(self):
        return f"{self.fecha} | {self.concepto.nombre} | ${self.monto}"
    
    @property
    def es_ingreso(self):
        return self.concepto.tipo == 'ingreso'
    
    @property
    def es_egreso(self):
        return self.concepto.tipo == 'egreso'



class HistorialPrecios(models.Model):
    """
    Guarda el historial de cambios en los precios
    Para auditoría y seguimiento
    """
    perfume = models.ForeignKey(
        Perfume, 
        on_delete=models.CASCADE, 
        related_name='historial_precios'
    )
    presentacion = models.ForeignKey(
        Presentacion, 
        on_delete=models.CASCADE, 
        related_name='historial_precios'
    )
    precio_anterior = models.DecimalField(max_digits=10, decimal_places=2)
    precio_nuevo = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_cambio = models.DateTimeField(auto_now_add=True)
    motivo = models.CharField(max_length=255, blank=True, null=True)
    usuario = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        verbose_name = "historial de precio"
        verbose_name_plural = "historial de precios"
        ordering = ["-fecha_cambio"]
    
    def __str__(self):
        return f"{self.perfume.nombre} - {self.presentacion.volumen_ml}ml: ${self.precio_anterior} → ${self.precio_nuevo}"
    

class CompraDecant(models.Model):
    """Compra de decants para prueba/venta sin frasco completo"""
    perfume = models.ForeignKey(
        Perfume,
        on_delete=models.PROTECT,
        related_name='compras_decant'
    )
    proveedor = models.CharField(max_length=200, blank=True, null=True)
    volumen_ml = models.PositiveIntegerField(help_text="Volumen del decant en ml")
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    costo_total = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    fecha_compra = models.DateField(default=timezone.now)
    notas = models.TextField(blank=True, null=True)
    movimiento_contable = models.ForeignKey(
        'Movimiento',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='compras_decant_asociadas'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "compra de decant"
        verbose_name_plural = "compras de decants"
        ordering = ['-fecha_compra']

    def __str__(self):
        return f"Decant #{self.id} - {self.perfume.nombre} {self.volumen_ml}ml x{self.cantidad}"

    def save(self, *args, **kwargs):
        self.costo_total = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)

    def procesar(self):
        """Agrega stock a la presentación decant correspondiente y crea movimiento"""
        presentacion, _ = Presentacion.objects.get_or_create(
            perfume=self.perfume,
            tipo='decant',
            volumen_ml=str(self.volumen_ml),
            defaults={'precio': 0, 'stock': 0, 'activo': True, 'precio_automatico': False}
        )
        presentacion.stock += self.cantidad
        presentacion.save()

        concepto, _ = Concepto.objects.get_or_create(
            nombre='Compra de decant',
            defaults={'tipo': 'egreso'}
        )
        movimiento = Movimiento.objects.create(
            concepto=concepto,
            monto=self.costo_total,
            cantidad=self.cantidad,
            descripcion=f"Decant #{self.id} - {self.perfume.nombre} {self.volumen_ml}ml",
            fecha=self.fecha_compra,
            estado='confirmado',
        )
        self.movimiento_contable = movimiento
        self.save()
        return True


class CompraInsumo(models.Model):
    """Compra de insumos: bolsas, frascos, jeringas, impresora, etc."""
    CATEGORIA_CHOICES = [
        ('empaque', 'Empaque (bolsas, cajas)'),
        ('decant', 'Material decant (frascos, jeringas)'),
        ('impresion', 'Impresión (impresora, cinta, etiquetas)'),
        ('otro', 'Otro'),
    ]

    nombre = models.CharField(max_length=200)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='otro')
    proveedor = models.CharField(max_length=200, blank=True, null=True)
    cantidad = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    costo_total = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    fecha_compra = models.DateField(default=timezone.now)
    notas = models.TextField(blank=True, null=True)

    # Opcional: vincular al inventario si quieres llevar stock
    inventario = models.ForeignKey(
        Inventario,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='compras_insumo',
        help_text="Vincula al inventario para actualizar stock automáticamente"
    )
    movimiento_contable = models.ForeignKey(
        'Movimiento',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='compras_insumo_asociadas'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "compra de insumo"
        verbose_name_plural = "compras de insumos"
        ordering = ['-fecha_compra']

    def __str__(self):
        return f"{self.nombre} x{self.cantidad} — ${self.costo_total}"

    def save(self, *args, **kwargs):
        self.costo_total = self.cantidad * self.precio_unitario
        # Actualizar inventario si está vinculado
        if self.inventario and not self.pk:  # solo en creación
            self.inventario.cantidad += self.cantidad
            self.inventario.save()
        super().save(*args, **kwargs)

    def registrar_movimiento(self):
        concepto, _ = Concepto.objects.get_or_create(
            nombre='Compra de insumo',
            defaults={'tipo': 'egreso'}
        )
        movimiento = Movimiento.objects.create(
            concepto=concepto,
            monto=self.costo_total,
            cantidad=self.cantidad,
            descripcion=f"Insumo: {self.nombre}",
            fecha=self.fecha_compra,
            estado='confirmado',
        )
        self.movimiento_contable = movimiento
        self.save()
        return movimiento


