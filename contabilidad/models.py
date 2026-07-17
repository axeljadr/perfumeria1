from django.db import models
from django.utils import timezone
from decimal import Decimal
import math
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
        """
        Procesa la compra completa:
        1. Actualiza stock de presentaciones
        2. Calcula precios de decants automáticos
        3. Crea movimiento contable
        """
        if self.estado == 'completada':
            raise ValueError("Esta compra ya fue procesada")
        
        # 1. Calcular precios de decants
        precios_decants = self.calcular_precios_decants()
        
        # 2. Crear/actualizar presentación 100ml (original)
        original, _ = Presentacion.objects.get_or_create(
            perfume=self.perfume,
            tipo='original',
            volumen_ml='100',
            defaults={
                'precio': self.perfume.precio_venta_completo if hasattr(self.perfume, 'precio_venta_completo') else 0,
                'stock': 0,
                'activo': True,
                'precio_automatico': False
            }
        )
        original.stock += self.cantidad_comprada
        original.save()
        
        # 3. Crear/actualizar presentaciones decants
        for ml, precio in precios_decants.items():
            decant, _ = Presentacion.objects.get_or_create(
                perfume=self.perfume,
                tipo='decant',
                volumen_ml=str(ml),
                defaults={
                    'precio': precio,
                    'stock': 0,
                    'activo': True,
                    'precio_automatico': True
                }
            )
            # Calcular cuántos decants se pueden hacer (100ml / ml)
            cantidad_decants = int(100 / ml) * self.cantidad_comprada
            decant.stock += cantidad_decants
            decant.precio = precio
            decant.save()
        
        # 4. Crear movimiento contable
        concepto, _ = Concepto.objects.get_or_create(
            nombre='Compra de perfume',
            defaults={
                'tipo': 'egreso',
            }
        )
        
        movimiento = Movimiento.objects.create(
            concepto=concepto,
            monto=self.costo_total,
            cantidad=self.cantidad_comprada,
            descripcion=f"Compra #{self.id} - {self.perfume.nombre}",
            fecha=self.fecha_compra,
            estado='confirmado',
        )
        
        self.movimiento_contable = movimiento
        
        # 5. Marcar compra como completada
        self.estado = 'completada'
        self.save()
        
        return True


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