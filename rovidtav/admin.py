# -*- coding: utf-8 -*-

import os

from django import forms
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.shortcuts import redirect
from django import template

# from django.contrib.admin.models import LogEntry
from django_object_actions import DjangoObjectActions

from .models import (Attachment, City, Client, Device, DeviceType, Ticket,
                     TicketEvent, TicketType)


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


class DeviceInLine(ReadOnlyInline):

    ordering = ('-created_at',)
    # fields = ('event', 'remark', 'created_by', 'created_at')
    model = Device


class AttachmentForm(forms.ModelForm):

    _data = forms.CharField(label=u'File', widget=forms.FileInput())
    # name = forms.CharField(
    #    label=u'Név',
    #    required=False,
    #    widget=forms.TextInput(attrs={'placeholder': u'Maradhat üres'}))
    name = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        fields = ('ticket', '_data', 'remark')

    def clean__data(self):
        if '_data' in self.files:
            return self.files['_data'].read()

    def clean_name(self):
        if '_data' in self.files:
            return self.files['_data'].name


class AttachmentAdmin(admin.ModelAdmin):

    form = AttachmentForm

    def response_add(self, request, obj, post_url_continue=None):
        return redirect('/admin/rovidtav/ticket/{}/change'
                        ''.format(obj.ticket.pk))

    def get_model_perms(self, request):
        """
        Return empty perms dict thus hiding the model from admin index.
        """
        return {}


class AttachmentInline(ReadOnlyInline):

    fields = ('name', 'file_link', 'created_by', 'created_at')
    ordering = ('-created_at',)
    model = Attachment
    # show_change_link = True

    def file_link(self, obj):
        return (u'<a target="_blank" href="/api/v1/attachment/{}">'
                u'Megnyitás</a>'.format(obj.pk))

    file_link.allow_tags = True

    def get_readonly_fields(self, request, obj=None):
        return super(AttachmentInline, self).get_readonly_fields(request, obj) + ['file_link']


class ClientAdmin(admin.ModelAdmin):

    readonly_fields = ('created_by', )
    list_display = ('name', 'mt_id', 'city_name', 'address', 'created_at_fmt')

    def city_name(self, obj):
        return u'{} ({})'.format(obj.city.name, obj.city.zip)

    city_name.short_description = u'Település'

    def created_at_fmt(self, obj):
        return obj.created_at.strftime('%Y.%m.%d %H:%M')

    created_at_fmt.short_description = u'Létrehozva'


class TicketEventAdmin(admin.ModelAdmin):

    fields = ('remark', 'ticket', 'event')

    def response_add(self, request, obj, post_url_continue=None):
        return redirect('/admin/rovidtav/ticket/{}/change'
                        ''.format(obj.ticket.pk))

    def get_model_perms(self, request):
        """
        Return empty perms dict thus hiding the model from admin index.
        """
        return {}


class TicketEventInline(ReadOnlyInline):

    model = TicketEvent
    fields = ('event', 'remark', 'created_by', 'created_at')
    ordering = ('-created_at',)


class TicketAdmin(DjangoObjectActions, admin.ModelAdmin):

    list_display = ('client_name', 'client_mt_id', 'ext_id',
                    'city_name', 'address',
                    'ticket_type_short', 'created_at_fmt', 'owner', 'status')
    change_actions = ('new_comment', 'new_attachment')
    readonly_fields = ('created_by', 'created_at')
    exclude = ('additional',)
    search_fields = ('client__name', 'client__mt_id',
                     'ext_id', 'ticket_type__name', )

    inlines = [TicketEventInline, AttachmentInline]

    def ticket_type_short(self, obj):
        ttype = unicode(obj.ticket_type)
        return ttype[:25].strip() + u'...' if len(ttype) > 25 else ttype

    ticket_type_short.short_description = u'Jegy típus'

    def client_name(self, obj):
        return obj.client.name

    client_name.short_description = u'Ügyfél neve'

    def client_mt_id(self, obj):
        return obj.client.mt_id

    client_mt_id.short_description = u'MT ID'

    def city_name(self, obj):
        return u'{} ({})'.format(obj.city.name, obj.city.zip)

    city_name.short_description = u'Település'

    def created_at_fmt(self, obj):
        # return obj.created_at.strftime('%Y.%m.%d %H:%M')
        return obj.created_at.strftime('%Y.%m.%d')

    created_at_fmt.short_description = u'Létrehozva'

    def new_comment(self, request, obj):
        return redirect('/admin/rovidtav/ticketevent/add/?event=Megj'
                        '&ticket={}'.format(obj.pk))

    new_comment.label = u'+ Megjegyzés'

    def new_attachment(self, request, obj):
        return redirect('/admin/rovidtav/attachment/add/?'
                        '&ticket={}'.format(obj.pk))

    new_attachment.label = u'+ File'


admin.site.register(Attachment, AttachmentAdmin)
admin.site.register(City)
admin.site.register(Client, ClientAdmin)
admin.site.register(Device)
admin.site.register(DeviceType)
admin.site.register(Ticket, TicketAdmin)
admin.site.register(TicketEvent, TicketEventAdmin)
admin.site.register(TicketType)
