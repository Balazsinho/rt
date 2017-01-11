import json

from django import template
from django.core.urlresolvers import reverse
from django.forms import (ModelChoiceField, Select, ModelMultipleChoiceField,
                          SelectMultiple)
from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
from jet.utils import get_model_instance_label, get_app_list


register = template.Library()


def jsonify(obj):
    return json.dumps(obj)

register.filter('jsonify', jsonify)


@register.filter
def jet_select2_lookups_balazs(field):
    if hasattr(field, 'field') and isinstance(field.field, ModelChoiceField):
        qs = field.field.queryset
        model = qs.model

        if getattr(model, 'autocomplete_search_fields', ['name']) and getattr(field.field, 'autocomplete', True):
            choices = []
            app_label = model._meta.app_label
            model_name = model._meta.object_name

            attrs = {
                'class': 'ajax',
                'data-app-label': app_label,
                'data-model': model_name,
                'data-ajax--url': reverse('jet:model_lookup')
            }

            form = field.form
            initial_value = form.data.get(field.name) if form.data != {} else form.initial.get(field.name)

            if hasattr(field, 'field') and isinstance(field.field, ModelMultipleChoiceField):
                if initial_value:
                    initial_objects = model.objects.filter(pk__in=initial_value)
                    choices.extend(
                        [(initial_object.pk, get_model_instance_label(initial_object))
                            for initial_object in initial_objects]
                    )

                if isinstance(field.field.widget, RelatedFieldWidgetWrapper):
                    field.field.widget.widget = SelectMultiple(attrs)
                else:
                    field.field.widget = SelectMultiple(attrs)
                field.field.choices = choices
            elif hasattr(field, 'field') and isinstance(field.field, ModelChoiceField):
                if initial_value:
                    initial_object = model.objects.get(pk=initial_value)
                    attrs['data-object-id'] = initial_value
                    choices.append((initial_object.pk, get_model_instance_label(initial_object)))

                if isinstance(field.field.widget, RelatedFieldWidgetWrapper):
                    field.field.widget.widget = Select(attrs)
                else:
                    field.field.widget = Select(attrs)
                field.field.choices = choices

    return field


@register.assignment_tag(takes_context=True)
def jet_get_menu_stripped(context):

    def get_native_model_url(model):
        return model.get('admin_url', model.get('add_url'))

    app_list = get_app_list(context)

    current_found = False

    all_aps = []
    apps = []

    for app in app_list:
        if not current_found:
            for model in app['models']:
                if context['request'].path.startswith(get_native_model_url(model)):
                    model['current'] = True
                    current_found = True
                    break

            if not current_found and context['request'].path.startswith(app['app_url']):
                app['current'] = True
                current_found = True

        apps.append(app)
        all_aps.append(app)

    return {'apps': apps, 'pinned_apps': [], 'all_apps': all_aps}
