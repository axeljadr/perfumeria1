from django import forms
from .models import Proveedor, Cotizacion,FilaCotizacion, ColumnaCotizacion, CeldaCotizacion


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre', 'telefono', 'notas']
        widgets = {
            'notas': forms.Textarea(attrs={'rows': 2}),
        }


class CotizacionForm(forms.ModelForm):
    class Meta:
        model = Cotizacion
        fields = ['descripcion']