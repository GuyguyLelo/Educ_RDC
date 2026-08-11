"""Icônes SVG pour boutons (sprite #i-* dans base.html)."""
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def ico(name, css_class='btn-ico'):
    """Rend une icône du sprite : {% ico 'plus' %}"""
    return mark_safe(
        f'<svg class="{css_class}" aria-hidden="true" focusable="false">'
        f'<use href="#i-{name}" xlink:href="#i-{name}"></use></svg>'
    )
