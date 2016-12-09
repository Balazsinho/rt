# -*- coding: utf-8 -*-
import os
import re
from datetime import datetime

from django.contrib.contenttypes.forms import BaseGenericInlineFormSet
from django.shortcuts import redirect

from rovidtav.admin_helpers import (ReadOnlyTabularInline, ShowCalcFields,
                                    GenericReadOnlyInline, RemoveInlineAction,
                                    ReadOnlyStackedInline,)
from rovidtav.models import (Attachment, Ticket, Note,
                             TicketMaterial, TicketWorkItem, DeviceOwner)
from django.http.response import HttpResponseRedirect


class IndirectGenericInlineFormSet(BaseGenericInlineFormSet):
    """
    A formset for generic inline objects to a parent with indirect
    relation.
    """

    def __init__(self, data=None, files=None, instance=None, save_as_new=None,
                 prefix=None, queryset=None, **kwargs):
        if instance and hasattr(instance, self.through_field):
            instance = getattr(instance, self.through_field)
        super(IndirectGenericInlineFormSet, self).__init__(
            data, files, instance, save_as_new, prefix, queryset, **kwargs)


class TicketDeviceFormset(IndirectGenericInlineFormSet):
    through_field = 'client'


class AttachmentInline(RemoveInlineAction,
                       ShowCalcFields,
                       ReadOnlyStackedInline):

    fields = ('f_thumbnail', 'f_created')
    ordering = ('-created_at',)
    model = Attachment
    template = os.path.join('admin', 'edit_inline', 'attachment_stacked.html')
    extra = 0

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def _pimp_actions(self, actions, obj):
        confirm_txt = (u'onclick="return confirm(\'Név: {} - '
                       u'Törlés?\')"'.format(obj.name))
        return self._add_action_attr(actions, '_action__remove__rovidtav__attachment', confirm_txt)

    def f_created(self, obj):
        created_at = obj.created_at.strftime('%Y-%m-%d %H:%M')
        return u'{} - {}'.format(obj.created_by, created_at)

    def f_thumbnail(self, obj):
        if obj.is_image():
            clickable_txt = (u'<img src="/api/v1/thumbnail/{}" />'
                             u''.format(obj.pk))
            download = u' download="{}"'.format(obj.name)
        else:
            clickable_txt = obj.name
            download = u''
        return (u'<a target="_blank" href="/api/v1/attachment/{}"{}>'
                u'{}</a>'.format(obj.pk, download, clickable_txt))

    f_thumbnail.allow_tags = True
    f_thumbnail.short_description = u'Megnyitás'


class MaterialInline(RemoveInlineAction,
                     ShowCalcFields,
                     ReadOnlyTabularInline):

    """
    Material inline for the ticket page
    """

    model = TicketMaterial
    fields = ('f_material_name', 'f_material_category', 'amount',
              'f_material_unit', 'f_material_comes_from', )
    verbose_name = u'Anyag'
    verbose_name_plural = u'Anyagok'
    ordering = ('-created_at',)

    def f_material_name(self, obj):
        return obj.material.name

    f_material_name.short_description = u'Anyag'

    def f_material_category(self, obj):
        return obj.material.category.name

    f_material_category.short_description = u'Anyag típus'

    def f_material_unit(self, obj):
        return obj.material.unit

    f_material_unit.short_description = u'Egység'

    def f_material_comes_from(self, obj):
        return obj.material.comes_from

    f_material_comes_from.short_description = u'Biztosítja'


class WorkItemInline(RemoveInlineAction,
                     ShowCalcFields, ReadOnlyTabularInline):

    """
    Workitem inline for the ticket page
    """

    model = TicketWorkItem
    fields = ('f_workitem_name', 'f_art_number', 'f_workitem_art_price',)
    verbose_name = u'Munka'
    verbose_name_plural = u'Munkák'
    ordering = ('work_item__art_number',)

    def f_workitem_name(self, obj):
        return obj.work_item.name

    f_workitem_name.short_description = u'Megnevezés'

    def f_art_number(self, obj):
        return obj.work_item.art_number

    f_art_number.short_description = u'Tételszám'

    def f_workitem_art_price(self, obj):
        return obj.work_item.art_price

    f_workitem_art_price.short_description = u'Tétel ár'

    def f_workitem_bulk_price(self, obj):
        return obj.work_item.bulk_price

    f_workitem_bulk_price.short_description = u'3. csop anyagárral'

    def f_workitem_given_price(self, obj):
        return obj.work_item.given_price

    f_workitem_given_price.short_description = u'Szerződött tétel ár'


class TicketInline(ShowCalcFields, ReadOnlyTabularInline):

    """
    Ticket inline for the client page
    """

    model = Ticket
    fields = ('f_ticket_link', 'address', 'owner', 'status',
              'f_created_at_fmt')
    ordering = ('-created_at',)

    def f_ticket_link(self, obj):
        return (u'<a href="/admin/rovidtav/ticket/{}/change">{}</a>'
                u''.format(obj.pk, unicode(obj)))

    f_ticket_link.allow_tags = True
    f_ticket_link.short_description = u'Jegy'

    def f_created_at_fmt(self, obj):
        return obj.created_at.strftime('%Y.%m.%d')

    f_created_at_fmt.short_description = u'Létrehozva'


class HistoryInline(GenericReadOnlyInline):

    # consider jet CompactInline
    verbose_name = u'Történet'
    verbose_name_plural = u'Történet'
    model = Note
    fields = ('remark', 'created_by', 'created_at')
    ordering = ('-created_at',)

    def get_queryset(self, request):
        qs = super(HistoryInline, self).get_queryset(request)
        return qs.filter(is_history=True)


class NoteInline(GenericReadOnlyInline):

    # consider jet CompactInline
    verbose_name = u'Megjegyzés'
    verbose_name_plural = u'Megjegyzések'
    model = Note
    fields = ('remark', 'created_by', 'created_at')
    ordering = ('-created_at',)

    def get_queryset(self, request):
        qs = super(NoteInline, self).get_queryset(request)
        return qs.filter(is_history=False)


class DeviceInline(ShowCalcFields, GenericReadOnlyInline):

    model = DeviceOwner
    fields = ('f_type_name', 'f_sn')

    def f_type_name(self, obj):
        return obj.device.type.name

    f_type_name.short_description = u'Típus'

    def f_sn(self, obj):
        return obj.device.sn

    f_type_name.short_description = u'Vonalkód'


class TicketDeviceInline(RemoveInlineAction,
                         ShowCalcFields,
                         GenericReadOnlyInline):

    verbose_name = u'Eszköz'
    verbose_name_plural = u'Eszközök'
    model = DeviceOwner
    formset = TicketDeviceFormset
    fields = ['f_type_name', 'f_sn']

    def _pimp_actions(self, actions, obj):
        return actions.replace(
            '<input ', '<input onclick="return confirm(\'SN: {} - '
                       'Leszerel?\')" '.format(obj.device.sn))

    def remove(self, request, ticket, dev_owner):
        dev_owner.owner = request.user
        dev_owner.device.returned_at = datetime.now()
        dev_owner.device.save()
        dev_owner.save()

    remove.short_description = u'Leszerel'

    def f_type_name(self, obj):
        return obj.device.type.name

    f_type_name.short_description = u'Típus'

    def f_sn(self, obj):
        return obj.device.sn

    f_sn.short_description = u'Vonalkód'
