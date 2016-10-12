# -*- coding: utf-8 -*-

from rovidtav.admin_helpers import ReadOnlyInline
from rovidtav.models import Attachment, Ticket, TicketEvent, Device


class AttachmentInline(ReadOnlyInline):

    fields = ('name', 'file_link', 'created_by', 'created_at')
    ordering = ('-created_at',)
    model = Attachment

    def file_link(self, obj):
        return (u'<a target="_blank" href="/api/v1/attachment/{}">'
                u'Megnyitás</a>'.format(obj.pk))

    file_link.allow_tags = True

    def get_readonly_fields(self, request, obj=None):
        return super(AttachmentInline, self).get_readonly_fields(request, obj) + ['file_link']


class TicketInline(ReadOnlyInline):

    """
    Ticket inline for the client page
    """

    model = Ticket
    fields = ('ticket_type_short', 'address', 'ticket_link', 'owner',
              'status', 'created_at_fmt')
    ordering = ('-created_at',)

    def ticket_link(self, obj):
        return ('<a href="/admin/rovidtav/ticket/{}/change">{}</a>'
                ''.format(obj.pk, obj.ext_id))

    ticket_link.allow_tags = True
    ticket_link.short_description = u'Jegy'

    def created_at_fmt(self, obj):
        return obj.created_at.strftime('%Y.%m.%d')

    created_at_fmt.short_description = u'Létrehozva'

    def ticket_type_short(self, obj):
        ttype = unicode(obj.ticket_type)
        return ttype[:35].strip() + u'...' if len(ttype) > 25 else ttype

    ticket_type_short.short_description = u'Jegy típus'

    def get_readonly_fields(self, request, obj=None):
        f = super(TicketInline, self).get_readonly_fields(request, obj)
        return f + ['ticket_link', 'created_at_fmt', 'ticket_type_short']


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


class DeviceInline(ReadOnlyInline):

    model = Device
    fields = ('type_name', 'sn', 'remark')
    ordering = ('-created_at',)

    def type_name(self, obj):
        return obj.type.name

    type_name.short_description = u'Típus'
