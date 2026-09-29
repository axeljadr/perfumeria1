from django import template

register = template.Library()

@register.filter
def rango(numero):
    return range(numero)

@register.filter
def rango_vacio(numero, total=5):
    return range(total - numero)