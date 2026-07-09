from django import forms
from .models import Perfume, Presentacion, FamiliaOlfativa, Acorde, Nota



class PerfumeForm(forms.ModelForm):
    class Meta:
        model = Perfume
        fields = [
            'nombre', 'marca', 'genero', 'familia_olfativa',
            'acordes', 'notas', 'longevidad', 'estela', 'uso',
            'descripcion', 'imagen_portada', 'activo'
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'acordes': forms.CheckboxSelectMultiple(),
            'notas': forms.CheckboxSelectMultiple(),
        }

class PresentacionForm(forms.ModelForm):
    class Meta:
        model = Presentacion
        fields = ['tipo', 'volumen_ml', 'precio', 'stock', 'activo']


# Formset para agregar varias presentaciones al mismo tiempo
PresentacionFormSet = forms.inlineformset_factory(
    Perfume,
    Presentacion,
    form=PresentacionForm,
    extra=2,
    can_delete=True
)

class FamiliaOlfativaForm(forms.ModelForm):
    class Meta:
        model = FamiliaOlfativa
        fields = ['nombre']



class AcordeForm(forms.ModelForm):
    class Meta:
        model = Acorde
        fields = ['nombre']


class NotaForm(forms.ModelForm):
    class Meta:
        model = Nota
        fields = ['nombre', 'imagen']

class PresentacionForm(forms.ModelForm):
    class Meta:
        model = Presentacion
        fields = ['tipo', 'volumen_ml', 'precio', 'stock', 'activo']