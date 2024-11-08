from django import template

register = template.Library()

@register.filter
def pluck(value, key):
    return [item.get(key) for item in value if key in item]
