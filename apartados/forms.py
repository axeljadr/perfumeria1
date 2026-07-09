from django import forms
from .models import PedidoApartado, PedidoApartadoItem, PagoApartado
from catalogo.models import Presentacion


class PedidoApartadoForm(forms.ModelForm):
    class Meta:
        model = PedidoApartado
        fields = ['cliente_nombre', 'cliente_telefono', 'cliente_ref', 'notas']
        widgets = {
            'cliente_nombre': forms.TextInput(attrs={
                'placeholder': 'Nombre completo del cliente'
            }),
            'cliente_telefono': forms.TextInput(attrs={
                'placeholder': 'WhatsApp / Teléfono'
            }),
            'cliente_ref': forms.TextInput(attrs={
                'placeholder': 'Facebook, Instagram, referido por...'
            }),
            'notas': forms.Textarea(attrs={
                'rows': 3, 'placeholder': 'Observaciones generales del pedido'
            }),
        }


class PedidoApartadoItemForm(forms.ModelForm):
    class Meta:
        model = PedidoApartadoItem
        fields = ['presentacion', 'cantidad', 'precio_unitario']
        widgets = {
            'cantidad': forms.NumberInput(attrs={
                'min': 1, 'value': 1
            }),
            'precio_unitario': forms.NumberInput(attrs={
                'step': '0.01', 'placeholder': 'Se autocompleta al seleccionar'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['presentacion'].queryset = (
            Presentacion.objects
            .filter(activo=True)
            .select_related('perfume')
            .order_by('perfume__marca', 'perfume__nombre', 'volumen_ml')
        )
        self.fields['presentacion'].widget.attrs.update({
            'class': 'item-presentacion'
        })
        self.fields['precio_unitario'].widget.attrs.update({
            'class': 'item-precio'
        })


PedidoApartadoItemFormSet = forms.inlineformset_factory(
    PedidoApartado,
    PedidoApartadoItem,
    form=PedidoApartadoItemForm,
    extra=0,
    can_delete=True,
    min_num=1,
    validate_min=True
)


class PagoApartadoForm(forms.ModelForm):
    class Meta:
        model = PagoApartado
        fields = ['fecha', 'monto', 'metodo', 'comprobante', 'observaciones']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'monto': forms.NumberInput(attrs={
                'step': '0.01', 'placeholder': '0.00'
            }),
            'observaciones': forms.Textarea(attrs={
                'rows': 2, 'placeholder': 'Opcional'
            }),
        }