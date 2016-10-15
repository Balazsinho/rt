# -*- coding: utf-8 -*-

import os

from django.contrib import admin
from django.http.response import HttpResponseRedirect
from django.contrib.admin.views.main import ChangeList, ORDER_VAR
from django_object_actions.utils import DjangoObjectActions


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


class ReadOnlyInline(admin.TabularInline):

    extra = 0
    can_delete = False
    template = os.path.join('admin', 'readOnlyInline.html')

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


class ShowCalcFields(object):
    def get_readonly_fields(self, request, obj=None):
        fields = [f for f in dir(self) if f.startswith('f_')]
        return super(ShowCalcFields, self).get_readonly_fields(request, obj) + fields


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
