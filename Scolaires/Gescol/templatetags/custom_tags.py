from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def startswith(value, prefix):
    """Custom template filter for string.startswith(prefix)"""
    return value.startswith(prefix) if value else False

@register.filter
def dict_items(dictionary):
    """Convert a dictionary to a list of (key, value) tuples for template iteration."""
    if dictionary:
        return list(dictionary.items())
    return []

