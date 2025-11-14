from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def abs_value(value):
    """Return the absolute value of a number"""
    try:
        if isinstance(value, (int, float, Decimal)):
            return abs(value)
        return value
    except (TypeError, ValueError):
        return value

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def mul(value, arg):
    """Multiply the value by the argument (alias for multiply)"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def divide(value, arg):
    """Divide the value by the argument"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return value

@register.filter
def subtract(value, arg):
    """Subtract the argument from the value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def percentage_change(current, previous):
    """Calculate percentage change between current and previous values"""
    try:
        if float(previous) == 0:
            return 0.0
        return ((float(current) - float(previous)) / float(previous)) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        return 0.0

@register.filter
def dict_get(mapping, key):
    """Safely get a value from a dict-like object by key"""
    try:
        return mapping.get(key, '')
    except Exception:
        return ''