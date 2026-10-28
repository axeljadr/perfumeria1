from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q, Case, When, Value, BooleanField
from .models import Perfume, FamiliaOlfativa, Acorde, Nota, Presentacion
from .forms import PerfumeForm, FamiliaOlfativaForm, AcordeForm, NotaForm, PresentacionForm
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from django.utils.http import url_has_allowed_host_and_scheme
from urllib.parse import urlencode
from django_ratelimit.decorators import ratelimit
from django.urls import reverse
from django.core.paginator import Paginator

def obtener_ip_cliente(group, request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()

    return request.META.get('REMOTE_ADDR', '')

@ratelimit(key=obtener_ip_cliente, rate='40/m', block=True)
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

    # Orden (con desempate por id para que la paginación sea estable)
    ORDENES_VALIDOS = {
        "nombre",
        "-nombre",
        "marca",
        "-marca",
        "creado_en",
        "-creado_en",
    }
    orden = request.GET.get("orden")
    if orden in ORDENES_VALIDOS:
        perfumes = perfumes.order_by(orden, "-id")
    else:
        perfumes = perfumes.order_by("-creado_en", "-id")

    # Paginación: 20 por página
    paginator = Paginator(perfumes, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Querystring sin "page" para conservar los filtros en los enlaces
    params = request.GET.copy()
    params.pop("page", None)

    context = {
        "perfumes": page_obj,
        "page_obj": page_obj,
        "querystring": params.urlencode(),
        "generos": Perfume.GENERO_CHOICES,
        "longevidad_opciones": Perfume.LONGEVIDAD_CHOICES,
        "estela_opciones": Perfume.ESTELA_CHOICES,
        "uso_opciones": Perfume.USO_CHOICES,
    }

    return render(request, "catalogo.html", context)

@ratelimit(key=obtener_ip_cliente, rate='40/m', block=True)
def detalle_perfume(request, pk):
    perfume = get_object_or_404(Perfume, pk=pk, activo=True)
    presentaciones = perfume.presentaciones.filter(activo=True)
    presentaciones_admin = perfume.presentaciones.all().order_by('tipo', 'volumen_ml')
    return render(request, 'perfum_detail.html', {
        'perfume': perfume,
        'presentaciones': presentaciones,
        'presentaciones_admin': presentaciones_admin,
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
            next_url = request.GET.get('next')

            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(f'{next_url}?{urlencode({"perfume_id": perfume.pk})}')

            return redirect('detalle_perfume', pk=perfume.pk)
    else:
        form = PerfumeForm(instance=perfume)

    return render(request, 'perfum_create.html', {
        'form': form,
        'editando': True,
        'perfume': perfume,
    })
@staff_member_required
def eliminar_perfume(request, pk):
    perfume = get_object_or_404(Perfume, pk=pk)
    if request.method == 'POST':
        perfume.delete()
        return redirect('catalogo')
    return redirect('detalle_perfume', pk=pk)

from django.http import JsonResponse

@ratelimit(key=obtener_ip_cliente, rate='40/m', block=True)
def buscar_familia(request):
    q = request.GET.get('q', '').strip()
    resultados = FamiliaOlfativa.objects.filter(nombre__icontains=q).values('id', 'nombre')[:10]
    return JsonResponse(list(resultados), safe=False)

@ratelimit(key=obtener_ip_cliente, rate='40/m', block=True)
def buscar_acorde(request):
    q = request.GET.get('q', '').strip()
    resultados = Acorde.objects.filter(nombre__icontains=q).values('id', 'nombre')[:10]
    return JsonResponse(list(resultados), safe=False)

@ratelimit(key=obtener_ip_cliente, rate='40/m', block=True)
def buscar_nota(request):
    q = request.GET.get('q', '').strip()
    resultados = Nota.objects.filter(nombre__icontains=q).values('id', 'nombre')[:10]
    return JsonResponse(list(resultados), safe=False)

@staff_member_required
def crear_familia(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if nombre:
            obj, _ = FamiliaOlfativa.objects.get_or_create(nombre__iexact=nombre, defaults={'nombre': nombre})
            return JsonResponse({'id': obj.id, 'nombre': obj.nombre})
    return JsonResponse({'error': 'Nombre requerido'}, status=400)

@staff_member_required
def crear_acorde(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if nombre:
            obj, _ = Acorde.objects.get_or_create(nombre__iexact=nombre, defaults={'nombre': nombre})
            return JsonResponse({'id': obj.id, 'nombre': obj.nombre})
    return JsonResponse({'error': 'Nombre requerido'}, status=400)

@staff_member_required
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
        form = FamiliaOlfativaForm(request.POST, request.FILES)
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
    form = FamiliaOlfativaForm(request.POST or None, request.FILES or None, instance=familia)
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

def _foto(perfume):
    if not perfume.imagen_portada:
        return ""
    try:
        return perfume.imagen_portada.build_url(
            width=120, height=120, crop="fill", quality="auto", fetch_format="auto"
        )
    except Exception:
        return perfume.imagen_portada.url


def _ml(p):
    try:
        return float(p.volumen_ml)
    except (TypeError, ValueError):
        return 0

 
def api_buscar_perfumes(request):
    q = request.GET.get("q", "").strip()
    qs = Perfume.objects.filter(activo=True).prefetch_related("presentaciones")
    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(marca__icontains=q))
    qs = qs.order_by("marca", "nombre")[:10]

    resultados = []
    for perfume in qs:
        pres = sorted(
            (p for p in perfume.presentaciones.all() if p.activo),
            key=_ml,
        )
        serializar = lambda p: {
            "id": p.id,
            "ml": p.volumen_ml,
            "precio": float(p.precio),
            "stock": p.stock,
            "tipo": p.get_tipo_display(),
        }
        decants = [serializar(p) for p in pres if p.tipo == 'decant']
        originales = [serializar(p) for p in pres if p.tipo != 'decant']
        todos = decants + originales

        resultados.append({
            'id': perfume.id,
            'nombre': perfume.nombre,
            'marca': perfume.marca,
            'foto': _foto(perfume),
            'url': reverse('detalle_perfume', args=[perfume.pk]),
            'desde': min((p['precio'] for p in todos), default=None),
            'precio_original': originales[0]['precio'] if originales else None,
            'originales': originales,
            'decants': decants,
        })

    return JsonResponse({"resultados": resultados})

def _tag(obj):
    return {
        "nombre": obj.nombre,
        "color": getattr(obj, "color", "") or "",
        "color_texto": getattr(obj, "color_texto", "") or "",
        "color_borde": getattr(obj, "color_borde", "") or "",
    }

def api_detalle_perfume(request, pk):
    # Público: el catálogo no exige login
    perfume = get_object_or_404(
        Perfume.objects.select_related("familia_olfativa").prefetch_related(
            "acordes", "notas", "presentaciones"
        ),
        pk=pk,
        activo=True,
    )

    def ml(p):
        try:
            return float(p.volumen_ml)
        except (TypeError, ValueError):
            return 0

    pres = sorted(
        (p for p in perfume.presentaciones.all() if p.activo),
        key=lambda p: (p.tipo != "decant", ml(p)),
    )

    return JsonResponse(
        {
            "id": perfume.id,
            "nombre": perfume.nombre,
            "marca": perfume.marca,
            "genero": perfume.get_genero_display(),
            "descripcion": perfume.descripcion,
            "foto": perfume.imagen_portada.url if perfume.imagen_portada else "",
            "url": reverse("detalle_perfume", args=[perfume.pk]),
            "familia": perfume.familia_olfativa.nombre
            if perfume.familia_olfativa
            else "",
            "acordes": [_tag(a) for a in perfume.acordes.all()],
            "notas": [_tag(n) for n in perfume.notas.all()],
            "longevidad": {
                "texto": perfume.get_longevidad_display(),
                "nivel": perfume.longevidad_nivel,
            },
            "estela": {
                "texto": perfume.get_estela_display(),
                "nivel": perfume.estela_nivel,
            },
            "uso": perfume.get_uso_display(),
            "presentaciones": [
                {
                    "id": p.id,
                    "tipo": p.get_tipo_display(),
                    "ml": p.volumen_ml,
                    "precio": float(p.precio),
                    "disponible": p.stock > 0,
                }
                for p in pres
            ],
        }
    )