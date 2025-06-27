# accounts/templatetags/profile_filters.py
from django import template
import os

register = template.Library()


@register.filter
def basename(value):
    """Returns the filename without path"""
    if value:
        return os.path.basename(str(value))
    return ''


@register.filter
def default_if_none(value, default):
    """Returns default if value is None"""
    return default if value is None else value


@register.filter
def join_list(value, separator=', '):
    """Joins a list with a separator"""
    if isinstance(value, list):
        return separator.join(str(item) for item in value)
    return value


@register.filter
def get_item(dictionary, key):
    """Gets an item from a dictionary"""
    return dictionary.get(key)


@register.filter
def multiply(value, arg):
    """Multiplies the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def basename(value):
    if value:
        return os.path.basename(value.name)
    return ''

@register.filter
def get_file_extension(value):
    if value:
        return os.path.splitext(value.name)[1]
    return ''

@register.filter
def filesize(value):
    """
    Format the file size into a human-readable string.
    """
    if not value:
        return "0 B"
    num = value
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"