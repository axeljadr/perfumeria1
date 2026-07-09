from django.db import models
from cloudinary.models import CloudinaryField

class FamiliaOlfativa(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Acorde(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Nota(models.Model):
    nombre = models.CharField(max_length=100)
    imagen = models.ImageField(upload_to='notas/', blank=True, null=True)

    def __str__(self):
        return self.nombre


class Perfume(models.Model):

    GENERO_CHOICES = [
        ('hombre', 'Hombre'),
        ('mujer', 'Mujer'),
        ('unisex', 'Unisex'),
    ]

    LONGEVIDAD_CHOICES = [
        ('baja', 'Baja (1-3h)'),
        ('moderada', 'Moderada (4-6h)'),
        ('alta', 'Alta (7-10h)'),
        ('muy_alta', 'Muy Alta (10h+)'),
    ]

    ESTELA_CHOICES = [
        ('intima', 'Íntima'),
        ('moderada', 'Moderada'),
        ('fuerte', 'Fuerte'),
        ('muy_fuerte', 'Muy Fuerte'),
    ]

    USO_CHOICES = [
        ('dia', 'Día'),
        ('noche', 'Noche'),
        ('ambos', 'Día y Noche'),
    ]

    # Info básica
    nombre = models.CharField(max_length=200)
    marca = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    genero = models.CharField(max_length=10, choices=GENERO_CHOICES)

    # Clasificación olfativa
    familia_olfativa = models.ForeignKey(
        FamiliaOlfativa, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='perfumes'
    )
    acordes = models.ManyToManyField(Acorde, blank=True, related_name='perfumes')
    notas = models.ManyToManyField(Nota, blank=True, related_name='perfumes')

    # Perfil olfativo
    longevidad = models.CharField(max_length=10, choices=LONGEVIDAD_CHOICES, blank=True)
    estela = models.CharField(max_length=10, choices=ESTELA_CHOICES, blank=True)
    uso = models.CharField(max_length=10, choices=USO_CHOICES, blank=True)

    imagen_portada = CloudinaryField('imagen', folder='perfumes/portadas', blank=True, null=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.marca} - {self.nombre}"


class ImagenPerfume(models.Model):
    """Múltiples imágenes por perfume para el diseñador gráfico"""

    TIPO_CHOICES = [
        ('principal', 'Principal'),
        ('catalogo', 'Catálogo'),
        ('historia', 'Historia/Story'),
        ('banner', 'Banner'),
        ('otra', 'Otra'),
    ]

    perfume = models.ForeignKey(Perfume, on_delete=models.CASCADE, related_name='imagenes')
    imagen = models.ImageField(upload_to='perfumes/')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='principal')
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['creado_en']

    def __str__(self):
        return f"{self.perfume.nombre} - {self.tipo}"
    

class Presentacion(models.Model):
    TIPO_CHOICES = [
        ('decant', 'Decant'),
        ('original', 'Tamaño Original'),
        ('set', 'Set'),
        ('miniatura', 'Miniatura'),
        ('otro', 'Otro'),
    ]

    perfume = models.ForeignKey(Perfume, on_delete=models.CASCADE, related_name='presentaciones')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    volumen_ml = models.CharField(max_length=20)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.perfume.nombre} - {self.get_tipo_display()} {self.volumen_ml}ml"

    @property
    def disponible(self):
        return self.stock > 0
    
    @property
    def apartados_activos(self):
        """Cuántos pedidos activos (no entregados, no cancelados) tienen esta presentación."""
        from apartados.models import PedidoApartadoItem
        return PedidoApartadoItem.objects.filter(
            presentacion=self,
            pedido__estado__in=['abierto', 'liquidado']
        ).count()