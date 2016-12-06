# -*- coding: utf-8 -*-

import os
import re

from django.http.response import HttpResponseRedirect
from django.contrib import admin
from django.contrib.admin.views.main import ChangeList, ORDER_VAR
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.admin import GenericTabularInline

from django_object_actions.utils import DjangoObjectActions
from jet.admin import CompactInline
from inline_actions.admin import InlineActionsMixin

from rovidtav.models import DeviceOwner


class DeviceOwnerListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = u'Tulajdonos (szerelő)'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'owner_employee'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return [(u.pk, u.username) for u in User.objects.all()]

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (either '80s' or '90s')
        # to decide how to filter the queryset.

        if self.value():
            user_ct = ContentType.objects.get(app_label='auth', model='user')
            owned_device_pks = [o.device.pk for o in
                                DeviceOwner.objects.filter(
                                    content_type=user_ct,
                                    object_id=self.value())]
            return queryset.filter(pk__in=owned_device_pks)


class CustomDjangoObjectActions(DjangoObjectActions):

    """
    Addressing the problem that the css class of an action is referenced as
    "class" in the original version, which renders this attribute unusable
    if you want to use it with the classic
    function.attribute notation in the admin class
    """

    def _get_button_attrs(self, tool):
        default_attrs = {
            'class': self._get_attr(tool, 'css_class'),
            'title': self._get_attr(tool, 'short_description'),
        }
        # TODO: fix custom attrs
        custom_attrs = {}
        return default_attrs, custom_attrs

    def _get_attr(self, tool, attr, default=''):
        return getattr(tool, attr) if hasattr(tool, attr) else default


class SpecialOrderingChangeList(ChangeList):

    """ This is the class that will be overriden in order to
    change the way the admin_order_fields are read """

    def get_ordering(self, request, queryset):
        """ This is the function that will be overriden so the
        admin_order_fields can be used as lists of fields
        instead of just one field """
        params = self.params
        ordering = list(self.model_admin.get_ordering(request) or
                        self._get_default_ordering())
        if ORDER_VAR in params:
            ordering = []
            order_params = params[ORDER_VAR].split('.')
            for p in order_params:
                try:
                    _, pfx, idx = p.rpartition('-')
                    field_name = self.list_display[int(idx)]
                    order_field = self.get_ordering_field(field_name)
                    if not order_field:
                        continue
                    # Here's where all the magic is done: the new method can
                    # accept either a list of strings (fields) or a simple
                    # string (a single field)
                    if type(order_field) in (list, tuple):
                        for field in order_field:
                            ordering.append(pfx + field)
                    else:
                        ordering.append(pfx + order_field)
                except (IndexError, ValueError):
                    continue
        ordering.extend(queryset.query.order_by)
        pk_name = self.lookup_opts.pk.name
        if not (set(ordering) & set(['pk', '-pk', pk_name, '-' + pk_name])):
            ordering.append('pk')
        return ordering


class ReadOnlyInline(object):

    extra = 0
    can_delete = False

    def get_readonly_fields(self, request, obj=None):
        if obj:
            result = list(set(
                    [field.name for field in self.opts.local_fields] +
                    [field.name for field in self.opts.local_many_to_many]
                ))
            result.remove('id')
        else:
            result = []

        return result

    def has_add_permission(self, request):
        return False


class ReadOnlyTabularInline(ReadOnlyInline, admin.TabularInline):
    template = os.path.join('admin', 'readOnlyInline.html')


class ReadOnlyCompactInline(ReadOnlyInline, CompactInline):
    pass


class ReadOnlyStackedInline(ReadOnlyInline, admin.StackedInline):
    pass


class GenericReadOnlyInline(ReadOnlyInline, GenericTabularInline):
    template = os.path.join('admin', 'readOnlyInline.html')


class ShowCalcFields(object):

    def get_readonly_fields(self, request, obj=None):
        calc_fields = [f for f in dir(self) if f.startswith('f_')]
        orig = super(ShowCalcFields, self).get_readonly_fields(request, obj)
        return list(orig) + calc_fields


class CustomInlineActionsMixin(InlineActionsMixin):

    def _pimp_actions(self, actions, obj):
        return actions

    def _add_action_attr(self, actions, look_for, new_attr_str):
        actions_list = re.findall('<input[^>]+>', actions, re.I)
        for action in actions_list:
            if look_for in action:
                new_action = action.replace('<input ',
                                            u'<input {} '.format(new_attr_str))
                actions = actions.replace(action, new_action)
        return actions

    def render_actions(self, obj=None):
        actions = super(CustomInlineActionsMixin, self).render_actions(obj)
        return self._pimp_actions(actions, obj)

    render_actions.short_description = u'Lehetőségek'
    render_actions.allow_tags = True


class RemoveInlineAction(CustomInlineActionsMixin):

    actions = ['remove']

    def remove(self, request, ticket, obj):
        obj.delete()

    remove.short_description = u'T&ouml;rl&eacute;s'


class HideIcons(object):

    hide_add = True
    hide_edit = True

    def _hide_icons(self, form, fields, **kwargs):
        hide_add = kwargs.get('hide_add', self.hide_add)
        hide_edit = kwargs.get('hide_edit', self.hide_edit)
        for field in fields:
            form.base_fields[field].widget.can_add_related = not hide_add
            form.base_fields[field].widget.can_change_related = not hide_edit


class ModelAdminRedirect(admin.ModelAdmin):

    def response_add(self, request, obj):
        return self._redir(request) or \
            super(ModelAdminRedirect, self).response_add(request, obj)

    def response_change(self, request, obj):
        return self._redir(request) or \
            super(ModelAdminRedirect, self).response_change(request, obj)

    def response_delete(self, request, obj):
        return self._redir(request) or \
            super(ModelAdminRedirect, self).response_delete(request, obj)

    def _redir(self, request):
        if "next" in request.GET:
            return HttpResponseRedirect(request.GET['next'])
        return None


# ============================================================================
# METHODS
# ============================================================================

def is_site_admin(user):
    groups = [g.name for g in user.groups.all()]
    return 'admin' in groups or user.is_superuser


def get_technicians():
    group = Group.objects.get(name=u'Szerelő')
    return group.user_set.all()


def get_technician_choices():
    users = get_technicians()
    return sorted([(u.pk, u.username) for u in users], key=lambda x: x[1])
