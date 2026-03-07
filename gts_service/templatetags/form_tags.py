from django import template
from django.forms import BoundField, CheckboxInput
from django.utils.html import format_html
from django.utils.safestring import SafeString, mark_safe

register = template.Library()


@register.simple_tag
def field(bound_field: BoundField) -> SafeString:
    is_checkbox = isinstance(bound_field.field.widget, CheckboxInput)
    extra_class = " checkbox-field" if is_checkbox else ""

    if is_checkbox:
        widget_html = format_html(
            "<label>{} {}</label>",
            mark_safe(bound_field.as_widget()),
            bound_field.label,
        )
    else:
        widget_html = format_html(
            '<label for="{}">{}</label>{}',
            bound_field.id_for_label,
            bound_field.label,
            mark_safe(bound_field.as_widget()),
        )

    help_html: SafeString = mark_safe("")
    if bound_field.help_text:
        help_html = format_html('<p class="help-text">{}</p>', bound_field.help_text)

    errors_html = mark_safe(
        "".join(
            format_html('<span class="help-block">{}</span>', e)
            for e in bound_field.errors
        )
    )

    return format_html(
        '<div class="form-group{}" id="{}">{}{}{}</div>',
        extra_class,
        bound_field.html_name,
        widget_html,
        help_html,
        errors_html,
    )
