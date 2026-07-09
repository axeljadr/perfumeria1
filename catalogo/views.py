from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from .models import Perfume, FamiliaOlfativa, Acorde, Nota, Presentacion
from .forms import PerfumeForm, FamiliaOlfativaForm, AcordeForm, NotaForm, PresentacionForm


def catalogo(request):
    perfumes = Perfume.objects.filter(activo=True).prefetch_related('presentaciones')

    genero   = request.GET.get('genero')
    familia  = request.GET.get('familia')
    acorde   = request.GET.get('acorde')
    busqueda = request.GET.get('q')

    if genero:
        perfumes = perfumes.filter(genero=genero)
    if familia:
        perfumes = perfumes.filter(familia_olfativa__id=familia)
    if acorde:
        perfumes = perfumes.filter(acordes__id=acorde)
    if busqueda:
        perfumes = perfumes.filter(
            Q(nombre__icontains=busqueda) | Q(marca__icontains=busqueda)
        )

    return render(request, 'catalogo.html', {
        'perfumes': perfumes,
        'familias': FamiliaOlfativa.objects.all(),
        'acordes': Acorde.objects.all(),
        'generos': Perfume.GENERO_CHOICES,
    })


def detalle_perfume(request, pk):
    perfume = get_object_or_404(Perfume, pk=pk, activo=True)
    presentaciones = perfume.presentaciones.filter(activo=True)
    return render(request, 'perfum_detail.html', {
        'perfume': perfume,
        'presentaciones': presentaciones,
    })


@staff_member_required
def crear_perfume(request):
    if request.method == 'POST':
        form = PerfumeForm(request.POST, request.FILES)
        print(request.FILES)
        if form.is_valid():
            perfume = form.save()
            return redirect('detalle_perfume', pk=perfume.pk)
    else:
        form = PerfumeForm()

    return render(request, 'perfum_create.html', {
        'form': form,
        'editando': False,
    })


@staff_member_required
def editar_perfume(request, pk):
    perfume = get_object_or_404(Perfume, pk=pk)
    if request.method == 'POST':
        form = PerfumeForm(request.POST, request.FILES, instance=perfume)
        if form.is_valid():
            form.save()
            return redirect('detalle_perfume', pk=perfume.pk)
    else:
        form = PerfumeForm(instance=perfume)

    return render(request, 'perfum_create.html', {
        'form': form,
        'editando': True,
        'perfume': perfume,
    })



# ── FAMILIAS OLFATIVAS ──────────────────────────────────────────

@staff_member_required
def familias_lista(request):
    familias = FamiliaOlfativa.objects.all().order_by('nombre')
    form = FamiliaOlfativaForm()

    if request.method == 'POST':
        form = FamiliaOlfativaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('familias_lista')

    return render(request, 'familias.html', {
        'familias': familias,
        'form': form,
    })


@staff_member_required
def familia_editar(request, pk):
    familia = get_object_or_404(FamiliaOlfativa, pk=pk)
    form = FamiliaOlfativaForm(request.POST or None, instance=familia)
    if form.is_valid():
        form.save()
        return redirect('familias_lista')
    return render(request, 'edit_item.html', {
        'form': form,
        'titulo': f'Editar familia: {familia.nombre}',
        'cancelar_url': 'familias_lista',
    })


@staff_member_required
def familia_eliminar(request, pk):
    familia = get_object_or_404(FamiliaOlfativa, pk=pk)
    if request.method == 'POST':
        familia.delete()
        return redirect('familias_lista')
    return render(request, 'confirmar_eliminar.html', {
        'objeto': familia.nombre,
        'cancelar_url': 'familias_lista',
    })


# ── ACORDES ─────────────────────────────────────────────────────

@staff_member_required
def acordes_lista(request):
    acordes = Acorde.objects.all().order_by('nombre')
    form = AcordeForm()

    if request.method == 'POST':
        form = AcordeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('acordes_lista')

    return render(request, 'acordes.html', {
        'acordes': acordes,
        'form': form,
    })


@staff_member_required
def acorde_editar(request, pk):
    acorde = get_object_or_404(Acorde, pk=pk)
    form = AcordeForm(request.POST or None, instance=acorde)
    if form.is_valid():
        form.save()
        return redirect('acordes_lista')
    return render(request, 'edit_item.html', {
        'form': form,
        'titulo': f'Editar acorde: {acorde.nombre}',
        'cancelar_url': 'acordes_lista',
    })


@staff_member_required
def acorde_eliminar(request, pk):
    acorde = get_object_or_404(Acorde, pk=pk)
    if request.method == 'POST':
        acorde.delete()
        return redirect('acordes_lista')
    return render(request, 'confirmar_eliminar.html', {
        'objeto': acorde.nombre,
        'cancelar_url': 'acordes_lista',
    })


# ── NOTAS ────────────────────────────────────────────────────────

@staff_member_required
def notas_lista(request):
    notas = Nota.objects.all().order_by('nombre')
    form = NotaForm()

    if request.method == 'POST':
        form = NotaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('notas_lista')

    return render(request, 'notas.html', {
        'notas': notas,
        'form': form,
    })


@staff_member_required
def nota_editar(request, pk):
    nota = get_object_or_404(Nota, pk=pk)
    form = NotaForm(request.POST or None, request.FILES or None, instance=nota)
    if form.is_valid():
        form.save()
        return redirect('notas_lista')
    return render(request, 'edit_item.html', {
        'form': form,
        'titulo': f'Editar nota: {nota.nombre}',
        'cancelar_url': 'notas_lista',
    })


@staff_member_required
def nota_eliminar(request, pk):
    nota = get_object_or_404(Nota, pk=pk)
    if request.method == 'POST':
        nota.delete()
        return redirect('notas_lista')
    return render(request, 'confirmar_eliminar.html', {
        'objeto': nota.nombre,
        'cancelar_url': 'notas_lista',
    })






@staff_member_required
def presentacion_crear(request, perfume_pk):
    perfume = get_object_or_404(Perfume, pk=perfume_pk)
    if request.method == 'POST':
        form = PresentacionForm(request.POST)
        if form.is_valid():
            presentacion = form.save(commit=False)
            presentacion.perfume = perfume
            presentacion.save()
            return redirect('detalle_perfume', pk=perfume.pk)
    else:
        form = PresentacionForm()
    return render(request, 'presentacion_form.html', {
        'form': form,
        'perfume': perfume,
        'editando': False,
    })


@staff_member_required
def presentacion_editar(request, pk):
    presentacion = get_object_or_404(Presentacion, pk=pk)
    perfume = presentacion.perfume
    if request.method == 'POST':
        form = PresentacionForm(request.POST, instance=presentacion)
        if form.is_valid():
            form.save()
            return redirect('detalle_perfume', pk=perfume.pk)
    else:
        form = PresentacionForm(instance=presentacion)
    return render(request, 'presentacion_form.html', {
        'form': form,
        'perfume': perfume,
        'editando': True,
        'presentacion': presentacion,
    })


@staff_member_required
def presentacion_eliminar(request, pk):
    presentacion = get_object_or_404(Presentacion, pk=pk)
    perfume = presentacion.perfume
    if request.method == 'POST':
        presentacion.delete()
        return redirect('detalle_perfume', pk=perfume.pk)
    return render(request, 'confirmar_eliminar.html', {
        'objeto': f'{presentacion.get_tipo_display()} {presentacion.volumen_ml}',
        'cancelar_url': 'detalle_perfume',
        'cancelar_pk': perfume.pk,
    })