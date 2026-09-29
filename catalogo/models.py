from django.db import models
import colorsys
from cloudinary.models import CloudinaryField
from PIL import Image
from io import BytesIO
import requests

def _color_borde_from_hex(hex_color):
    """Genera una versión más saturada y brillante del color para usar como borde."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return '#ffffff'
    try:
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    except ValueError:
        return '#ffffff'
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    # Aumenta saturación y ajusta luminosidad para un efecto brillante/neón
    s = min(1.0, s + 0.4)
    l = min(0.75, max(0.35, l * 1.15))
    r2, g2, b2 = colorsys.hls_to_rgb(h, l, s)
    return '#{:02x}{:02x}{:02x}'.format(
        int(r2 * 255), int(g2 * 255), int(b2 * 255)
    )

class FamiliaOlfativa(models.Model):
    nombre = models.CharField(max_length=100)
    imagen_fondo = models.ImageField(upload_to='familias/fondos/', blank=True, null=True)

    def __str__(self):
        return self.nombre


class Acorde(models.Model):
    nombre = models.CharField(max_length=100)
    color = models.CharField(
        max_length=7, default='#e8e2d5',
        help_text='Color en formato hexadecimal, ej: #e8e2d5'
    )

    @property
    def color_texto(self):
        """Calcula si el texto debe ser blanco o negro según el brillo del color de fondo."""
        hex_color = self.color.lstrip('#')
        if len(hex_color) != 6:
            return '#000000'
        try:
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        except ValueError:
            return '#000000'
        luminancia = (0.299 * r + 0.587 * g + 0.114 * b)
        return '#000000' if luminancia > 150 else '#ffffff'
    @property
    def color_borde(self):
        return _color_borde_from_hex(self.color)

    def __str__(self):
        return self.nombre


class Nota(models.Model):
    nombre = models.CharField(max_length=100)
    imagen = models.ImageField(upload_to='notas/', blank=True, null=True)
    color = models.CharField(
        max_length=7, default='#e8e2d5',
        help_text='Color en formato hexadecimal, ej: #e8e2d5'
    )

    @property
    def color_texto(self):
        hex_color = self.color.lstrip('#')
        if len(hex_color) != 6:
            return '#000000'
        try:
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        except ValueError:
            return '#000000'
        luminancia = (0.299 * r + 0.587 * g + 0.114 * b)
        return '#000000' if luminancia > 150 else '#ffffff'
    @property
    def color_borde(self):
        return _color_borde_from_hex(self.color)

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
    color_ambiente = models.CharField(max_length=7, blank=True, null=True)
    
    def extraer_color_dominante(self):
        if not self.imagen_portada:
            return None
        try:
            url = self.imagen_portada.url
            response = requests.get(url, timeout=10)
            img = Image.open(BytesIO(response.content)).convert('RGB')
            img = img.resize((100, 100))
            paleta = img.quantize(colors=6, method=Image.MEDIANCUT)
            paleta_rgb = paleta.convert('RGB')
            colores = paleta_rgb.getcolors(100 * 100)
            colores.sort(key=lambda c: c[0], reverse=True)
            r, g, b = colores[0][1]
            return '#{:02x}{:02x}{:02x}'.format(r, g, b)
        except Exception as e:
            print("ERROR extrayendo color:", e)
            return None

    def save(self, *args, **kwargs):
        if self.imagen_portada:
            nuevo_color = self.extraer_color_dominante()
            if nuevo_color:
                self.color_ambiente = nuevo_color
        super().save(*args, **kwargs)


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
    precio_automatico = models.BooleanField(default=False, blank=True, null=True)

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
    
    class Meta:
        verbose_name = "presentación"
        verbose_name_plural = "presentaciones"
        ordering = ['perfume', 'volumen_ml']
        unique_together = ['perfume', 'tipo', 'volumen_ml']
    
    def __str__(self):
        return f"{self.perfume.nombre} - {self.get_tipo_display()} {self.volumen_ml}ml"


