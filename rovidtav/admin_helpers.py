# -*- coding: utf-8 -*-

import os

from django.contrib import admin
from django.http.response import HttpResponseRedirect


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
