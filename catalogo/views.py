from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q, Case, When, Value, BooleanField
from .models import Perfume, FamiliaOlfativa, Acorde, Nota, Presentacion
from .forms import PerfumeForm, FamiliaOlfativaForm, AcordeForm, NotaForm, PresentacionForm
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta


def catalogo(request):
    # Obtener todos los perfumes activos
    perfumes = Perfume.objects.filter(activo=True)
    
    # Calcular fecha límite
    hace_7_dias = timezone.now() - timedelta(days=7)
    
    # Añadir campo virtual es_nuevo usando annotate
    perfumes = perfumes.annotate(
        es_nuevo=Case(
            When(creado_en__gte=hace_7_dias, then=Value(True)),
            default=Value(False),
            output_field=BooleanField()
        )
    )
    
    # Filtros
    q = request.GET.get('q')
    if q:
        perfumes = perfumes.filter(nombre__icontains=q) | perfumes.filter(marca__icontains=q)

    genero = request.GET.get('genero')
    if genero:
        perfumes = perfumes.filter(genero=genero)

    familia = request.GET.get('familia')
    if familia and familia.isdigit():
        perfumes = perfumes.filter(familia_olfativa_id=familia)

    # Acordes (múltiple)
    acordes_ids = request.GET.getlist('acorde')
    acordes_ids = [id for id in acordes_ids if id and id.isdigit()]
    if acordes_ids:
        perfumes = perfumes.filter(acordes__id__in=acordes_ids).distinct()

    longevidad = request.GET.get('longevidad')
    if longevidad:
        perfumes = perfumes.filter(longevidad=longevidad)

    estela = request.GET.get('estela')
    if estela:
        perfumes = perfumes.filter(estela=estela)

    uso = request.GET.get('uso')
    if uso:
        perfumes = perfumes.filter(uso=uso)

    # Orden
    orden = request.GET.get('orden')
    if orden:
        perfumes = perfumes.order_by(orden)
    else:
        perfumes = perfumes.order_by('-creado_en')

    # Contexto
    context = {
        'perfumes': perfumes,  # Sigue siendo un queryset con el campo es_nuevo
        'generos': Perfume.GENERO_CHOICES,
        'familias': FamiliaOlfativa.objects.all(),
        'acordes': Acorde.objects.all(),
        'acordes_seleccionados': acordes_ids,
        'longevidad_opciones': Perfume.LONGEVIDAD_CHOICES,
        'estela_opciones': Perfume.ESTELA_CHOICES,
        'uso_opciones': Perfume.USO_CHOICES,
    }
    
    return render(request, 'catalogo.html', context)


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


from django.http import JsonResponse

def buscar_familia(request):
    q = request.GET.get('q', '').strip()
    resultados = FamiliaOlfativa.objects.filter(nombre__icontains=q).values('id', 'nombre')[:10]
    return JsonResponse(list(resultados), safe=False)

def buscar_acorde(request):
    q = request.GET.get('q', '').strip()
    resultados = Acorde.objects.filter(nombre__icontains=q).values('id', 'nombre')[:10]
    return JsonResponse(list(resultados), safe=False)

def buscar_nota(request):
    q = request.GET.get('q', '').strip()
    resultados = Nota.objects.filter(nombre__icontains=q).values('id', 'nombre')[:10]
    return JsonResponse(list(resultados), safe=False)

def crear_familia(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if nombre:
            obj, _ = FamiliaOlfativa.objects.get_or_create(nombre__iexact=nombre, defaults={'nombre': nombre})
            return JsonResponse({'id': obj.id, 'nombre': obj.nombre})
    return JsonResponse({'error': 'Nombre requerido'}, status=400)

def crear_acorde(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if nombre:
            obj, _ = Acorde.objects.get_or_create(nombre__iexact=nombre, defaults={'nombre': nombre})
            return JsonResponse({'id': obj.id, 'nombre': obj.nombre})
    return JsonResponse({'error': 'Nombre requerido'}, status=400)

def crear_nota(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if nombre:
            obj, _ = Nota.objects.get_or_create(nombre__iexact=nombre, defaults={'nombre': nombre})
            return JsonResponse({'id': obj.id, 'nombre': obj.nombre})
    return JsonResponse({'error': 'Nombre requerido'}, status=400)
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