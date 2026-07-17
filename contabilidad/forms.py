from django import forms
from django.utils import timezone
from .models import (
    Compra, Presentacion, Movimiento, Concepto, 
    ConfiguracionDecant, Perfume
)
from catalogo.models import Perfume  # Tu modelo existente


# ============================================================
# FORMULARIOS DE COMPRAS
# ============================================================

class CompraForm(forms.ModelForm):
    """Formulario para registrar una compra"""
    
    class Meta:
        model = Compra
        fields = [
            'perfume', 'proveedor', 'cantidad_comprada', 
            'precio_unitario', 'fecha_compra', 'notas'
        ]
        widgets = {
            'fecha_compra': forms.DateInput(attrs={'type': 'date'}),
            'notas': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Notas adicionales...'}),
        }
        labels = {
            'perfume': 'Perfume',
            'proveedor': 'Proveedor',
            'cantidad_comprada': 'Cantidad comprada (unidades)',
            'precio_unitario': 'Precio por unidad ($)',
            'fecha_compra': 'Fecha de compra',
            'notas': 'Notas',
        }
        help_texts = {
            'cantidad_comprada': 'Número de perfumes completos de 100ml',
            'precio_unitario': 'Precio al que compraste cada perfume',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo perfumes activos
        self.fields['perfume'].queryset = Perfume.objects.filter(activo=True)
        # Establecer fecha actual por defecto
        if not self.instance.pk:
            self.fields['fecha_compra'].initial = timezone.now().date()
    
    def clean(self):
        cleaned_data = super().clean()
        cantidad = cleaned_data.get('cantidad_comprada')
        precio_unitario = cleaned_data.get('precio_unitario')
        
        if cantidad and precio_unitario:
            # Calcular costo total automáticamente
            cleaned_data['costo_total'] = cantidad * precio_unitario
        
        return cleaned_data


class CompraProcesarForm(forms.Form):
    """Formulario para procesar una compra (confirmar)"""
    confirmar = forms.BooleanField(
        required=True,
        label='Confirmar procesamiento',
        help_text='Al procesar la compra se actualizará el inventario y se crearán los movimientos contables'
    )
    notas = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
        label='Notas adicionales'
    )


# ============================================================
# FORMULARIOS DE PRESENTACIONES
# ============================================================

class PresentacionForm(forms.ModelForm):
    """Formulario para gestionar presentaciones"""
    
    class Meta:
        model = Presentacion
        fields = ['tipo', 'volumen_ml', 'precio', 'stock', 'activo']
        widgets = {
            'volumen_ml': forms.TextInput(attrs={'placeholder': 'Ej: 3, 5, 10, 100'}),
        }
    
    def clean_volumen_ml(self):
        volumen = self.cleaned_data.get('volumen_ml')
        try:
            int(volumen)
        except ValueError:
            raise forms.ValidationError('El volumen debe ser un número entero')
        return volumen


class PresentacionBatchForm(forms.Form):
    """Formulario para crear múltiples presentaciones a la vez"""
    perfume = forms.ModelChoiceField(
        queryset=Perfume.objects.filter(activo=True),
        label='Perfume'
    )
    precios = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        help_text='Ingresa los precios en el formato: ml:precio (uno por línea)<br>Ejemplo:<br>3:45<br>5:60<br>10:105<br>100:650'
    )
    stock_inicial = forms.IntegerField(
        initial=0,
        required=False,
        label='Stock inicial (opcional)'
    )
    
    def clean_precios(self):
        data = self.cleaned_data.get('precios')
        lineas = data.strip().split('\n')
        precios = {}
        
        for linea in lineas:
            if ':' not in linea:
                raise forms.ValidationError(f'Formato incorrecto en: "{linea}". Usa ml:precio')
            try:
                ml, precio = linea.split(':')
                ml = int(ml.strip())
                precio = float(precio.strip())
                precios[ml] = precio
            except ValueError:
                raise forms.ValidationError(f'Error en: "{linea}". Asegúrate de usar números válidos')
        
        if not precios:
            raise forms.ValidationError('Debes ingresar al menos un precio')
        
        return precios


# ============================================================
# FORMULARIOS DE CONTABILIDAD
# ============================================================

class MovimientoForm(forms.ModelForm):
    """Formulario para crear movimientos contables"""
    
    class Meta:
        model = Movimiento
        fields = ['fecha', 'concepto', 'monto', 'cantidad', 'descripcion', 'estado']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'descripcion': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Descripción del movimiento...'}),
        }
        labels = {
            'fecha': 'Fecha',
            'concepto': 'Concepto',
            'monto': 'Monto ($)',
            'cantidad': 'Cantidad',
            'descripcion': 'Descripción',
            'estado': 'Estado',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['concepto'].queryset = Concepto.objects.all()
        if not self.instance.pk:
            self.fields['fecha'].initial = timezone.now().date()
            self.fields['estado'].initial = 'confirmado'


class MovimientoFiltroForm(forms.Form):
    """Formulario para filtrar movimientos"""
    fecha_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Fecha inicio'
    )
    fecha_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Fecha fin'
    )
    concepto = forms.ModelChoiceField(
        queryset=Concepto.objects.all(),
        required=False,
        label='Concepto'
    )
    tipo = forms.ChoiceField(
        choices=[('', 'Todos')] + Concepto.TIPO_CHOICES,
        required=False,
        label='Tipo'
    )
    estado = forms.ChoiceField(
        choices=[('', 'Todos')] + Movimiento.ESTADO_CHOICES,
        required=False,
        label='Estado'
    )


# ============================================================
# FORMULARIOS DE CONFIGURACIÓN
# ============================================================

class ConfiguracionDecantForm(forms.ModelForm):
    """Formulario para configurar los decants"""
    
    class Meta:
        model = ConfiguracionDecant
        fields = ['bolsa_costo', 'jeringa_costo', 'porcentaje_ganancia', 'redondeo_terminacion']
        labels = {
            'bolsa_costo': 'Costo de bolsa ($)',
            'jeringa_costo': 'Costo de jeringa ($)',
            'porcentaje_ganancia': 'Porcentaje de ganancia (%)',
            'redondeo_terminacion': 'Tipo de redondeo',
        }
        help_texts = {
            'bolsa_costo': 'Costo unitario de la bolsa para decant',
            'jeringa_costo': 'Costo unitario de la jeringa para decant',
            'porcentaje_ganancia': 'Porcentaje a agregar sobre el costo total',
            'redondeo_terminacion': 'Terminación para redondear los precios finales',
        }


# ============================================================
# FORMULARIOS DE REPORTES
# ============================================================

class ReporteForm(forms.Form):
    """Formulario para generar reportes"""
    TIPO_CHOICES = [
        ('compras', 'Reporte de Compras'),
        ('movimientos', 'Reporte de Movimientos'),
        ('inventario', 'Reporte de Inventario'),
        ('utilidades', 'Reporte de Utilidades'),
    ]
    FORMATO_CHOICES = [
        ('html', 'HTML'),
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
    ]
    
    tipo_reporte = forms.ChoiceField(choices=TIPO_CHOICES, label='Tipo de reporte')
    formato = forms.ChoiceField(choices=FORMATO_CHOICES, label='Formato')
    fecha_inicio = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Fecha inicio'
    )
    fecha_fin = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Fecha fin'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        
        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            raise forms.ValidationError('La fecha de inicio no puede ser mayor a la fecha fin')
        
        return cleaned_data