from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from catalogo.models import FamiliaOlfativa, Acorde, Nota, Perfume
from perfumeria.settings import MAKE_API_KEY

@api_view(['POST'])
def crear_perfume_completo(request):
    api_key = request.headers.get('X-API-Key')
    if api_key != MAKE_API_KEY:
        return Response({'error': 'No autorizado'}, status=401)
    data = request.data

    # 1. Familia olfativa (get o create)
    familia, _ = FamiliaOlfativa.objects.get_or_create(
        nombre__iexact=data.get('familia_olfativa', ''),
        defaults={'nombre': data.get('familia_olfativa', '')}
    )

    # 2. Mapear longevidad
    longevidad_map = {
        '1-3h': 'baja', '3-6h': 'moderada',
        '6h': 'moderada', '6-9h': 'alta',
        '9-12h': 'muy_alta', '+12h': 'muy_alta'
    }
    estela_map = {
        'suave': 'intima', 'moderada': 'moderada',
        'fuerte': 'fuerte', 'muy fuerte': 'muy_fuerte'
    }
    genero_map = {
        'femenino': 'mujer', 'masculino': 'hombre', 'unisex': 'unisex'
    }

    # 3. Crear perfume
    perfume, created = Perfume.objects.get_or_create(
        nombre__iexact=data.get('nombre', ''),
        marca__iexact=data.get('marca', ''),
        defaults={
            'nombre': data.get('nombre', ''),
            'marca': data.get('marca', ''),
            'genero': genero_map.get(data.get('genero', '').lower(), 'unisex'),
            'familia_olfativa': familia,
            'longevidad': longevidad_map.get(data.get('longevidad', '').lower(), 'moderada'),
            'estela': estela_map.get(data.get('estela', '').lower(), 'moderada'),
            'uso': data.get('uso', 'ambos'),
            'descripcion': data.get('descripcion', ''),
        }
    )

    if not created:
        return Response({'mensaje': 'Perfume ya existe', 'id': perfume.id}, status=200)

    # 4. Acordes M2M
    for nombre_acorde in data.get('acordes', []):
        acorde, _ = Acorde.objects.get_or_create(nombre__iexact=nombre_acorde,
                                                  defaults={'nombre': nombre_acorde})
        perfume.acordes.add(acorde)

    # 5. Notas M2M
    for nombre_nota in data.get('notas', []):
        nota, _ = Nota.objects.get_or_create(nombre__iexact=nombre_nota,
                                              defaults={'nombre': nombre_nota})
        perfume.notas.add(nota)

    return Response({'mensaje': 'Perfume creado', 'id': perfume.id}, status=201)