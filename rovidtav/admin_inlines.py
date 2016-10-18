# -*- coding: utf-8 -*-

from rovidtav.admin_helpers import ReadOnlyInline, ShowCalcFields
from rovidtav.models import (Attachment, Ticket, TicketEvent, Device,
                             TicketMaterial, TicketWorkItem)


class AttachmentInline(ShowCalcFields, ReadOnlyInline):

    fields = ('name', 'f_file_link', 'created_by', 'created_at')
    ordering = ('-created_at',)
    model = Attachment

    def f_file_link(self, obj):
        return (u'<a target="_blank" href="/api/v1/attachment/{}">'
                u'Megnyitás</a>'.format(obj.pk))

    f_file_link.allow_tags = True


class MaterialInline(ShowCalcFields, ReadOnlyInline):

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


class WorkItemInline(ShowCalcFields, ReadOnlyInline):

    """
    Workitem inline for the ticket page
    """

    model = TicketWorkItem
    fields = ('f_workitem_name', 'f_art_number', 'f_workitem_bulk_price',
              'f_workitem_given_price',)
    verbose_name = u'Munka'
    verbose_name_plural = u'Munkák'
    ordering = ('-created_at',)

    def f_workitem_name(self, obj):
        return obj.work_item.name

    f_workitem_name.short_description = u'Megnevezés'

    def f_art_number(self, obj):
        return obj.work_item.art_number

    f_art_number.short_description = u'Tételszám'

    def f_workitem_bulk_price(self, obj):
        return obj.work_item.bulk_price

    f_workitem_bulk_price.short_description = u'3. csop anyagárral'

    def f_workitem_given_price(self, obj):
        return obj.work_item.given_price

    f_workitem_given_price.short_description = u'Szerződött tétel ár'


class TicketInline(ShowCalcFields, ReadOnlyInline):

    """
    Ticket inline for the client page
    """

    model = Ticket
    fields = ('f_ticket_type_short', 'address', 'f_ticket_link', 'owner',
              'status', 'f_created_at_fmt')
    ordering = ('-created_at',)

    def f_ticket_link(self, obj):
        return ('<a href="/admin/rovidtav/ticket/{}/change">{}</a>'
                ''.format(obj.pk, obj.ext_id))

    f_ticket_link.allow_tags = True
    f_ticket_link.short_description = u'Jegy'

    def f_created_at_fmt(self, obj):
        return obj.created_at.strftime('%Y.%m.%d')

    f_created_at_fmt.short_description = u'Létrehozva'

    def f_ticket_type_short(self, obj):
        ttype = unicode(obj.ticket_type)
        return ttype[:35].strip() + u'...' if len(ttype) > 25 else ttype

    f_ticket_type_short.short_description = u'Jegy típus'


class HistoryInline(ReadOnlyInline):

    # consider jet CompactInline
    verbose_name = u'Történet'
    verbose_name_plural = u'Történet'
    model = TicketEvent
    fields = ('event', 'remark', 'created_by', 'created_at')
    ordering = ('-created_at',)

    def get_queryset(self, request):
        qs = super(HistoryInline, self).get_queryset(request)
        return qs.exclude(event='Megj')


class TicketEventInline(ReadOnlyInline):

    # consider jet CompactInline
    verbose_name = u'Megjegyzés'
    verbose_name_plural = u'Megjegyzések'
    model = TicketEvent
    fields = ('event', 'remark', 'created_by', 'created_at')
    ordering = ('-created_at',)

    def get_queryset(self, request):
        qs = super(TicketEventInline, self).get_queryset(request)
        return qs.filter(event='Megj')


class DeviceInline(ShowCalcFields, ReadOnlyInline):

    model = Device
    fields = ('f_type_name', 'sn', 'remark')

    def f_type_name(self, obj):
        return obj.type.name

    f_type_name.short_description = u'Típus'


class TicketDeviceInline(DeviceInline):

    model = Device
    fk_name = 'client__ticket'

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        """enable ordering drop-down alphabetically"""
        #if db_field.name == 'car':
        #    kwargs['queryset'] = Car.objects.order_by("name") 
        return super(TicketDeviceInline, self).formfield_for_foreignkey(db_field, request, **kwargs)
