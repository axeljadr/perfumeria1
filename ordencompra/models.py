from django.db import models

class Proveedor(models.Model):
    nombre = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20, blank=True)
    notas = models.TextField(blank=True)

    def __str__(self):
        return self.nombre

    class Meta:
        ordering = ['nombre']


class Cotizacion(models.Model):
    descripcion = models.CharField(max_length=200)
    fecha = models.DateTimeField(auto_now_add=True)
    cerrada = models.BooleanField(default=False)  # True = solo lectura

    def __str__(self):
        return f"{self.descripcion} ({self.fecha.strftime('%d/%m/%Y')})"

    class Meta:
        ordering = ['-fecha']


class FilaCotizacion(models.Model):
    """Un perfume dentro de la cotización (fila)"""
    cotizacion = models.ForeignKey(Cotizacion, on_delete=models.CASCADE, related_name='filas')
    perfume_nombre = models.CharField(max_length=200)
    orden = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.perfume_nombre

    class Meta:
        ordering = ['orden']


class ColumnaCotizacion(models.Model):
    """Un proveedor dentro de la cotización (columna)"""
    cotizacion = models.ForeignKey(Cotizacion, on_delete=models.CASCADE, related_name='columnas')
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE)
    envio = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.proveedor.nombre


class CeldaCotizacion(models.Model):
    """El precio que un proveedor da por un perfume (celda de la tabla)"""
    fila = models.ForeignKey(FilaCotizacion, on_delete=models.CASCADE, related_name='celdas')
    columna = models.ForeignKey(ColumnaCotizacion, on_delete=models.CASCADE, related_name='celdas')
    precio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('fila', 'columna')

    def __str__(self):
        return f"{self.fila.perfume_nombre} / {self.columna.proveedor.nombre}: ${self.precio}"