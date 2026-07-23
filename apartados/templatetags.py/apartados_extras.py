from django import template

register = template.Library()

@register.filter
def ocultar_nombre(nombre):
    if not nombre:
        return ""
    return "*" * (len(nombre) - 1) + nombre[-1]