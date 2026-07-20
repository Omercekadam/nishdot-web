"""
HTML Sanitizasyon Template Filtresi
====================================

Quill zengin metin editöründen gelen HTML'i (etkinlik açıklaması, yasal
belgeler) sunucu tarafında temizler. `|safe` yerine `|sanitize` kullanılır —
böylece staff/board hesaplarının ürettiği içerik yoluyla stored-XSS engellenir.

Kullanım (şablonda):
    {% load sanitize %}
    {{ event.description|sanitize }}
"""

import nh3
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Quill'in ürettiği zengin metin etiketleri. <script>, <style>, <iframe>,
# olay öznitelikleri (onclick vb.) beyaz listede DEĞİLDİR → temizlenir.
ALLOWED_TAGS = {
    "p", "br", "span", "div",
    "strong", "b", "em", "i", "u", "s", "strike", "sub", "sup",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "blockquote", "pre", "code",
    "a", "img",
    "hr",
    "table", "thead", "tbody", "tr", "th", "td",
}

ALLOWED_ATTRIBUTES = {
    # not: "rel" burada YOK — link_rel parametresi otomatik ekliyor.
    "a": {"href", "title", "target"},
    "img": {"src", "alt", "title", "width", "height"},
    "span": {"class", "style"},
    "p": {"class", "style"},
    "div": {"class", "style"},
    "ol": {"class"},
    "ul": {"class"},
    "li": {"class"},
    "*": {"class"},
}


@register.filter(name="sanitize")
def sanitize(value):
    """HTML'i güvenli bir alt kümeye indirger ve safe olarak işaretler."""
    if not value:
        return ""
    cleaned = nh3.clean(
        str(value),
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        link_rel="noopener noreferrer nofollow",
    )
    return mark_safe(cleaned)
