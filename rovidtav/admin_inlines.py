# -*- coding: utf-8 -*-
import os
from datetime import datetime

from django.contrib.contenttypes.forms import BaseGenericInlineFormSet
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from jet.admin import CompactInline

from rovidtav.admin_helpers import (
    ReadOnlyTabularInline, ShowCalcFields, GenericReadOnlyInline,
    RemoveInlineAction, ReadOnlyStackedInline, CustomInlineActionsMixin,
    GenericReadOnlyStackedInline, ReadOnlyCompactInline,
    GenericReadOnlyCompactInline)
from rovidtav.models import (
    Attachment, Ticket, Note, TicketMaterial, TicketWorkItem, DeviceOwner,
    SystemEmail, NTAttachment, NetworkTicketMaterial, NetworkTicketWorkItem,
    MMAttachment, MaterialMovementMaterial, WarehouseMaterial,
    DeviceReassignEvent, WarehouseLocation, Device)


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


class BaseAttachmentInline(RemoveInlineAction,
                           ShowCalcFields,
                           ReadOnlyStackedInline):

    fields = ('f_thumbnail', 'f_created')
    ordering = ('-created_at',)
    template = os.path.join('admin', 'edit_inline', 'attachment_stacked.html')
    extra = 0

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def remove(self, request, ticket, obj):
        super(BaseAttachmentInline, self).remove(request, ticket, obj)
        try:
            ticket.refresh_has_images()
        except AttributeError:
            # Not maintaining has_images boolean
            pass

    remove.onclick = u'return confirm(\'{name} - T&ouml;rl&eacute;s?\')'
    remove.short_description = u'T&ouml;rl&eacute;s'

    def f_created(self, obj):
        created_at = obj.created_at.strftime('%Y-%m-%d %H:%M')
        return u'{} - {}'.format(obj.created_by, created_at)

    def f_thumbnail(self, obj):
        if obj.is_image():
            clickable_txt = (u'<img src="/api/v1/{}/{}" />'
                             u''.format(self.thumbnail_lnk, obj.pk))
        else:
            clickable_txt = (u'<img src="/api/v1/{}/{}" />'
                             u'<br />{}'.format(self.thumbnail_lnk,
                                                obj.pk, obj.name))

        if obj.content_disposition.startswith(u'inline'):
            download = u''
        else:
            download = u' download="{}"'.format(obj.name)

        return (u'<a target="_blank" rel="noopener noreferrer" '
                u'href="/api/v1/{}/{}"{}>'
                u'{}</a>'.format(self.attachment_lnk, obj.pk,
                                 download, clickable_txt))

    f_thumbnail.allow_tags = True
    f_thumbnail.short_description = u'Megnyitás'


class AttachmentInline(BaseAttachmentInline):

    model = Attachment
    thumbnail_lnk = 'thumbnail'
    attachment_lnk = 'attachment'


class NTAttachmentInline(BaseAttachmentInline):

    model = NTAttachment
    thumbnail_lnk = 'ntthumbnail'
    attachment_lnk = 'ntattachment'


class MMAttachmentInline(BaseAttachmentInline):

    model = MMAttachment
    thumbnail_lnk = 'mmthumbnail'
    attachment_lnk = 'mmattachment'


class BaseMaterialInline(ShowCalcFields):

    """
    Material inline for the ticket page
    """

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


class MaterialInline(RemoveInlineAction, BaseMaterialInline,
                     ReadOnlyCompactInline):

    model = TicketMaterial


class NetworkMaterialInline(RemoveInlineAction, BaseMaterialInline,
                            ReadOnlyCompactInline):

    model = NetworkTicketMaterial


class MMMaterialInline(RemoveInlineAction, BaseMaterialInline,
                       CompactInline):

    model = MaterialMovementMaterial
    extra = 0


class MMMaterialReadonlyInline(BaseMaterialInline, ReadOnlyCompactInline):

    model = MaterialMovementMaterial
    extra = 0


class WarehouseMaterialInline(BaseMaterialInline, CompactInline):

    model = WarehouseMaterial
    extra = 0
    readonly_fields = ['amount']
    fields = ('f_material_name', 'location',
              'f_material_category', 'amount', 'f_material_unit', )


class BaseWorkItemInline(RemoveInlineAction,
                         ShowCalcFields, ReadOnlyCompactInline):

    """
    Workitem inline for the ticket page
    """

    fields = ('f_workitem_name', 'f_art_number', 'amount',
              'f_workitem_art_price', 'f_workitem_total_price')
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

    def f_workitem_total_price(self, obj):
        return obj.work_item.art_price * obj.amount

    f_workitem_total_price.short_description = u'Össz ár'

    def f_workitem_bulk_price(self, obj):
        return obj.work_item.bulk_price

    f_workitem_bulk_price.short_description = u'3. csop anyagárral'

    def f_workitem_given_price(self, obj):
        return obj.work_item.given_price

    f_workitem_given_price.short_description = u'Szerződött tétel ár'


class WorkItemInline(BaseWorkItemInline):

    model = TicketWorkItem


class NetworkWorkItemInline(BaseWorkItemInline):

    model = NetworkTicketWorkItem


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


class PayoffTicketInline(ShowCalcFields, ReadOnlyTabularInline):

    model = Ticket.payoffs.through
    ordering = []
    fields = ['f_ticket_link', 'f_ticket_created']
    verbose_name = u'Jegy'
    verbose_name_plural = u'Jegyek'

    def f_ticket_link(self, obj):
        return (u'<a href="/admin/rovidtav/ticket/{}/change">{}</a>'
                u''.format(obj.ticket.pk, unicode(obj.ticket)))

    f_ticket_link.allow_tags = True
    f_ticket_link.short_description = u'Jegy'

    def f_ticket_address(self, obj):
        return obj.ticket.address

    f_ticket_address.short_description = u'Cím'

    def f_ticket_owner(self, obj):
        return obj.ticket.owner

    f_ticket_owner.short_description = u'Szerelő'

    def f_ticket_status(self, obj):
        return obj.ticket.status

    f_ticket_status.short_description = u'Státusz'

    def f_ticket_created(self, obj):
        return obj.ticket.created_at.strftime('%Y.%m.%d')

    f_ticket_created.short_description = u'Létrehozva'


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


class NoteInline(GenericReadOnlyCompactInline):

    # consider jet CompactInline
    verbose_name = u'Megjegyzés'
    verbose_name_plural = u'Megjegyzések'
    model = Note
    fields = ('remark', 'created_by', 'created_at')
    ordering = ('-created_at',)

    def get_queryset(self, request):
        qs = super(NoteInline, self).get_queryset(request)
        return qs.filter(is_history=False)


class SystemEmailInline(GenericReadOnlyStackedInline):

    # consider jet CompactInline
    verbose_name = u'Email'
    verbose_name_plural = u'Emailek'
    model = SystemEmail
    fields = ('status', 'remark', 'created_by', 'created_at')
    ordering = ('-created_at',)


class DeviceTypeDeviceInline(ReadOnlyCompactInline):

    verbose_name = u'Eszköz'
    verbose_name_plural = u'Eszközök'
    model = Device


class DeviceInline(ShowCalcFields, GenericReadOnlyInline):

    verbose_name = u'Eszköz'
    verbose_name_plural = u'Eszközök'
    model = DeviceOwner
    fields = ('f_type_name', 'f_sn')

    def f_type_name(self, obj):
        return obj.device.type.name

    f_type_name.short_description = u'Típus'

    def f_sn(self, obj):
        return obj.device.sn

    f_sn.short_description = u'Vonalkód'


class TicketDeviceInline(CustomInlineActionsMixin,
                         ShowCalcFields,
                         GenericReadOnlyCompactInline):

    verbose_name = u'Eszköz'
    verbose_name_plural = u'Eszközök'
    model = DeviceOwner
    formset = TicketDeviceFormset
    fields = ['f_type_name', 'f_sn']
    actions = ['remove', 'modify']

    def remove(self, request, ticket, dev_owner):
        dev_owner.owner = request.user
        dev_owner.device.returned_at = datetime.now()
        dev_owner.device.save()
        dev_owner.save()

    def _evt_param(self, obj):
        if obj.__class__ == DeviceOwner:
            return obj.device
        return obj

    remove.short_description = u'Leszerel'
    remove.onclick = u'return confirm(\'{sn} - Leszerel?\')'

    def modify(self, request, ticket, dev_owner):
        dev = dev_owner.device
        info = (dev._meta.app_label, dev._meta.model_name)
        url = reverse('admin:%s_%s_change' % info, args=(dev.pk,))
        url = '{}?next={}%23/tab/inline_4/#/tab/module_0/'.format(url, request.path)
        return redirect(url, anchor='')

    modify.short_description = u'M&oacute;dos&iacute;t'

    def f_type_name(self, obj):
        return obj.device.type.name

    f_type_name.short_description = u'Típus'

    def f_sn(self, obj):
        return obj.device.sn

    f_sn.short_description = u'Vonalkód'


class MMDeviceInline(ShowCalcFields,
                     ReadOnlyCompactInline):

    verbose_name = u'Eszköz'
    verbose_name_plural = u'Eszközök'
    model = DeviceReassignEvent
    # formset = TicketDeviceFormset
    fields = ['f_type_name', 'f_sn']

    def _evt_param(self, obj):
        if obj.__class__ == DeviceOwner:
            return obj.device
        return obj

    def modify(self, request, _, dev_owner):
        dev = dev_owner.device
        info = (dev._meta.app_label, dev._meta.model_name)
        url = reverse('admin:%s_%s_change' % info, args=(dev.pk,))
        url = '{}?next={}%23/tab/inline_3/#/tab/module_0/'.format(url, request.path)
        return redirect(url, anchor='')

    modify.short_description = u'M&oacute;dos&iacute;t'

    def f_type_name(self, obj):
        return obj.device.type.name

    f_type_name.short_description = u'Típus'

    def f_sn(self, obj):
        return obj.device.sn

    f_sn.short_description = u'Vonalkód'


class WarehouseDeviceInline(CustomInlineActionsMixin, ShowCalcFields,
                            GenericReadOnlyCompactInline):

    verbose_name = u'Eszköz'
    verbose_name_plural = u'Eszközök'
    model = DeviceOwner
    # formset = TicketDeviceFormset
    fields = ['f_type_name', 'f_sn']
    actions = ['delete', 'modify']

    def delete(self, request, _, dev_owner):
        dev_owner.device.delete()
        dev_owner.delete()

    delete.short_description = u'T&ouml;r&ouml;l'
    delete.onclick = u'return confirm(\'{sn} - Biztosan t&ouml;r&ouml;l?\')'

    def _evt_param(self, obj):
        if obj.__class__ == DeviceOwner:
            return obj.device
        return obj

    def modify(self, request, _, dev_owner):
        dev = dev_owner.device
        info = (dev._meta.app_label, dev._meta.model_name)
        url = reverse('admin:%s_%s_change' % info, args=(dev.pk,))
        url = '{}?next={}%23/tab/inline_3/#/tab/module_0/'.format(url, request.path)
        return redirect(url, anchor='')

    modify.short_description = u'M&oacute;dos&iacute;t'

    def f_type_name(self, obj):
        return obj.device.type.name

    f_type_name.short_description = u'Típus'

    def f_sn(self, obj):
        return obj.device.sn

    f_sn.short_description = u'Vonalkód'


class WarehouseLocationInline(ReadOnlyCompactInline):

    model = WarehouseLocation
