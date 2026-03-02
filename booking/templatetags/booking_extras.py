"""Custom template tags and filters for SmartQueue AI."""

from django import template

register = template.Library()


@register.filter
def replace(value, arg):
    """Replace occurrences of arg[0] with arg[1] in value. Usage: value|replace:"old,new" """
    if ',' in arg:
        old, new = arg.split(',', 1)
        return str(value).replace(old, new)
    return value


@register.filter
def split(value, arg):
    """Split a string by arg. Usage: value|split:',' """
    return str(value).split(arg)
