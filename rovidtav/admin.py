# -*- coding: utf-8 -*-

from django import forms
from django.contrib import admin
from django.shortcuts import redirect
from django.contrib.admin.filters import SimpleListFilter
from django_object_actions import DjangoObjectActions

from daterange_filter.filter import DateRangeFilter

from .admin_helpers import (ModelAdminRedirect, SpecialOrderingChangeList)
from .admin_inlines import (AttachmentInline, DeviceInline, TicketEventInline,
                            TicketInline)
from .models import (Attachment, City, Client, Device, DeviceType, Ticket,
                     TicketEvent, TicketType)
from rovidtav.models import Payoff


class AttachmentForm(forms.ModelForm):

    _data = forms.CharField(label=u'File', widget=forms.FileInput())
    name = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        fields = ('ticket', '_data', 'remark')

    def clean__data(self):
        if '_data' in self.files:
            return self.files['_data'].read()

    def clean_name(self):
        if '_data' in self.files:
            return self.files['_data'].name


class AttachmentAdmin(ModelAdminRedirect):

    form = AttachmentForm

    def get_model_perms(self, request):
        # Hide from admin index
        return {}


class PayoffAdmin(admin.ModelAdmin):

    list_display = ('name', 'remark')
    inlines = (TicketInline,)


class CityAdmin(admin.ModelAdmin):

    list_display = ('name', 'zip', 'primer', 'onuk')


class ClientAdmin(admin.ModelAdmin):

    readonly_fields = ('created_by', )
    list_display = ('name', 'mt_id', 'city_name', 'address', 'created_at_fmt')
    inlines = (TicketInline,)

    def city_name(self, obj):
        return u'{} ({})'.format(obj.city.name, obj.city.zip)

    city_name.short_description = u'Település'

    def created_at_fmt(self, obj):
        return obj.created_at.strftime('%Y.%m.%d %H:%M')

    created_at_fmt.short_description = u'Létrehozva'


class TicketEventAdmin(ModelAdminRedirect):

    fields = ('remark', 'ticket', 'event')

    def get_model_perms(self, request):
        # Hide from admin index
        return {}


class IsClosedFilter(SimpleListFilter):
    title = u'Státusz'

    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return (
            (None, u''),
            ('all', u'Mind'),
            ('open', u'Nyitott'),
            ('closed', u'Lezárt'),
        )

    def choices(self, cl):
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == lookup,
                'query_string': cl.get_query_string({
                    self.parameter_name: lookup,
                }, []),
                'display': title,
            }

    def queryset(self, request, queryset):
        if self.value() is None:
            self.used_parameters[self.parameter_name] = 'open'

        if self.value() == 'open':
            return queryset.filter(status__in=(u'Új', u'Kiadva',
                                               u'Folyamatban'))
        elif self.value() == 'closed':
            return queryset.filter(status__in=(u'Lezárva',
                                               u'Duplikált'))
        elif self.value() == 'all':
            return queryset


class TicketAdmin(DjangoObjectActions, admin.ModelAdmin):

    list_per_page = 500
    list_display = ('address', 'city_name', 'client_name', 'client_link',
                    'ticket_type_short', 'created_at_fmt', 'owner', 'status',
                    'primer', 'payoff_link')
    # TODO: check if this is useful
    # list_editable = ('owner', )
    exclude = ('additional',)
    search_fields = ('client__name', 'client__mt_id', 'city__name',
                     'city__zip', 'ext_id', 'ticket_type__name', 'address',)

    inlines = (TicketEventInline, AttachmentInline)
    ordering = ('created_at',)

    def get_changelist(self, request, **kwargs):
        return SpecialOrderingChangeList

    def changelist_view(self, request, extra_context=None):
        """
        We need to remove the links to the client and the payoff if the user
        is not an admin
        """
        response = super(TicketAdmin, self).changelist_view(request,
                                                            extra_context)
        if not request.user.is_superuser:
            subst = {'payoff_link': 'payoff_name',
                     'client_link': 'client_mt_id',
                     }
            columns = response.context_data['cl'].list_display
            new_cols = [subst.get(c, c) for c in columns]
            response.context_data['cl'].list_display = new_cols
        return response

    def get_actions(self, request):
        actions = super(TicketAdmin, self).get_actions(request)
        del actions['delete_selected']
        return actions

    def get_change_actions(self, request, object_id, form_url):
        obj = Ticket.objects.get(pk=object_id)
        if request.user.is_superuser or \
                obj.status in (u'Kiadva', u'Folyamatban'):
            return ('new_comment', 'new_attachment')
        else:
            return ('new_comment',)

    def get_list_filter(self, request):
        if hasattr(request, 'user'):
            if request.user.is_superuser:
                return (('created_at', DateRangeFilter),
                        'city__primer', 'owner', IsClosedFilter)
            else:
                return (IsClosedFilter,)

    def lookup_allowed(self, key, value):
        if key in ('city__primer',):
            return True
        return super(TicketAdmin, self).lookup_allowed(key, value)

    def get_queryset(self, request):
        qs = super(TicketAdmin, self).get_queryset(request)
        if hasattr(request, 'user'):
            if request.user.is_superuser:
                return qs
            return qs.filter(owner=request.user)
        return qs

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ('created_by', 'created_at')
        else:
            fields = ('ext_id', 'client', 'ticket_type', 'city',
                      'address', 'owner', 'created_by', 'created_at',
                      'payoff')
            if obj.status not in (u'Kiadva', u'Folyamatban'):
                fields += ('status',)
            return fields

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super(TicketAdmin, self).get_inline_instances(request, obj=None)

    # =========================================================================
    # FIELDS
    # =========================================================================

    def payoff_link(self, obj):
        if obj.payoff:
            return ('<a href="/admin/rovidtav/payoff/{}/change">{}</a>'
                    ''.format(obj.payoff.pk, obj.payoff.name))
        else:
            return None

    payoff_link.allow_tags = True
    payoff_link.short_description = u'Elszámolás'

    def payoff_name(self, obj):
        if obj.payoff:
            return obj.payoff.name
        else:
            return None

    payoff_name.short_description = u'Elszámolás'

    def client_link(self, obj):
        return ('<a href="/admin/rovidtav/client/{}/change">{}</a>'
                ''.format(obj.client.pk, obj.client.mt_id))
    client_link.allow_tags = True
    client_link.short_description = u'Ügyfél'

    def client_mt_id(self, obj):
        return obj.client.mt_id

    client_mt_id.short_description = u'MT ID'

    def client_name(self, obj):
        return obj.client.name

    client_name.short_description = u'Ügyfél neve'

    def ticket_type_short(self, obj):
        ttype = unicode(obj.ticket_type)
        return ttype[:25].strip() + u'...' if len(ttype) > 25 else ttype

    ticket_type_short.short_description = u'Jegy típus'

    def primer(self, obj):
        return obj.city.primer

    primer.short_description = u'Primer'
    primer.admin_order_field = 'city__primer'

    def city_name(self, obj):
        return u'{} {}'.format(obj.city.zip, obj.city.name)

    city_name.short_description = u'Település'
    city_name.admin_order_field = 'city__name'

    def created_at_fmt(self, obj):
        # return obj.created_at.strftime('%Y.%m.%d %H:%M')
        return obj.created_at.strftime('%Y.%m.%d')

    created_at_fmt.short_description = u'Létrehozva'
    created_at_fmt.admin_order_field = ('created_at')

    def new_comment(self, request, obj):
        return redirect('/admin/rovidtav/ticketevent/add/?event=Megj&ticket={}'
                        '&next=/admin/rovidtav/ticket/{}/change/#/tab/'
                        'inline_0/'.format(obj.pk, obj.pk))

    new_comment.label = u'+ Megjegyzés'

    def new_attachment(self, request, obj):
        return redirect('/admin/rovidtav/attachment/add/?ticket={}&next='
                        '/admin/rovidtav/ticket/{}/change/#/tab/inline_1/'
                        ''.format(obj.pk, obj.pk))

    new_attachment.label = u'+ File'


admin.site.register(Attachment, AttachmentAdmin)
admin.site.register(City, CityAdmin)
admin.site.register(Payoff, PayoffAdmin)
admin.site.register(Client, ClientAdmin)
admin.site.register(Device)
admin.site.register(DeviceType)
admin.site.register(Ticket, TicketAdmin)
admin.site.register(TicketEvent, TicketEventAdmin)
admin.site.register(TicketType)
