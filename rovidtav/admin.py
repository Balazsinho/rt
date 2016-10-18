# -*- coding: utf-8 -*-

import os

from django import forms
from django.contrib import admin
from django.shortcuts import redirect
from django.contrib.admin.filters import SimpleListFilter

from daterange_filter.filter import DateRangeFilter

from .admin_helpers import (ModelAdminRedirect, SpecialOrderingChangeList,
                            CustomDjangoObjectActions, is_site_admin)
from .admin_inlines import (AttachmentInline, DeviceInline, TicketEventInline,
                            TicketInline, HistoryInline, MaterialInline,
                            WorkItemInline, TicketDeviceInline)
from .models import (Attachment, City, Client, Device, DeviceType, Ticket,
                     TicketEvent, TicketType, MaterialCategory, Material,
                     TicketMaterial, WorkItem, TicketWorkItem, Payoff,
                     Engineer)

from django.forms.models import ModelChoiceField


# ============================================================================
# FORMS
# ============================================================================


class AttachmentForm(forms.ModelForm):

    _data = forms.CharField(label=u'File', widget=forms.FileInput())
    name = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        fields = ('ticket', '_data', 'remark')
        widgets = {
          'ticket': forms.HiddenInput(),
        }

    def clean__data(self):
        if '_data' in self.files:
            return self.files['_data'].read()

    def clean_name(self):
        if '_data' in self.files:
            return self.files['_data'].name


class TicketMaterialForm(forms.ModelForm):
    material = ModelChoiceField(
        Material.objects.all(),
        widget=forms.Select(attrs={'style': 'width:500px', 'size': '10'}),
        label='Anyag',
    )

    def __init__(self, *args, **kwargs):
        super(TicketMaterialForm, self).__init__(*args, **kwargs)
        ticket_id = kwargs.get('initial', {}).get('ticket')
        if ticket_id:
            ticket = Ticket.objects.get(pk=kwargs['initial']['ticket'])
            suggestions = Material.objects.filter(technology=ticket.technology())
            self.fields['material'].queryset = suggestions

    class Meta:
        model = TicketMaterial
        widgets = {
          'ticket': forms.HiddenInput(),
        }
        fields = '__all__'


class TicketWorkItemForm(forms.ModelForm):
    work_item = ModelChoiceField(
        WorkItem.objects.all(),
        widget=forms.Select(attrs={'style': 'width:500px', 'size': '10'}),
        label='Munka',
    )

    def __init__(self, *args, **kwargs):
        super(TicketWorkItemForm, self).__init__(*args, **kwargs)

    class Meta:
        model = TicketWorkItem
        widgets = {
          'ticket': forms.HiddenInput(),
        }
        fields = '__all__'


# ============================================================================
# MODELADMIN CLASSSES
# ============================================================================


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


class DeviceAdmin(admin.ModelAdmin):

    list_display = ('sn', 'device_type', 'owner', 'client_link')
    search_fields = ('client__name', 'client__mt_id', 'type__name',
                     'sn')
    list_filter = ('type__name', 'owner')

    def device_type(self, obj):
        return obj.type.name

    device_type.short_description = u'Típus'

    def client_link(self, obj):
        if obj.client:
            return ('<a href="/admin/rovidtav/client/{}/change">{}</a>'
                    ''.format(obj.client.pk, obj.client.mt_id))
    client_link.allow_tags = True
    client_link.short_description = u'Ügyfél'


class ClientAdmin(admin.ModelAdmin):

    readonly_fields = ('created_by', )
    list_display = ('name', 'mt_id', 'city_name', 'address', 'created_at_fmt')
    inlines = (TicketInline, DeviceInline)

    def city_name(self, obj):
        return u'{} ({})'.format(obj.city.name, obj.city.zip)

    city_name.short_description = u'Település'

    def created_at_fmt(self, obj):
        return obj.created_at.strftime('%Y.%m.%d %H:%M')

    created_at_fmt.short_description = u'Létrehozva'


class MaterialAdmin(admin.ModelAdmin):

    list_display = ('sn', 'name', 'category', 'price', 'unit', 'comes_from')
    search_fields = ('sn', 'name', 'category__name')
    list_filter = ('category__name', )


class TicketMaterialAdmin(ModelAdminRedirect):

    form = TicketMaterialForm
    change_form_template = os.path.join('rovidtav', 'select2_wide.html')

    def get_model_perms(self, request):
        # Hide from admin index
        return {}


class TicketWorkItemAdmin(ModelAdminRedirect):

    form = TicketWorkItemForm
    change_form_template = os.path.join('rovidtav', 'select2_wide.html')

    def get_model_perms(self, request):
        # Hide from admin index
        return {}


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


class TicketAdmin(CustomDjangoObjectActions, admin.ModelAdmin):

    # =========================================================================
    # PARAMETERS
    # =========================================================================

    list_per_page = 500
    list_display = ('address', 'city_name', 'client_name', 'client_link',
                    'ticket_type', 'created_at_fmt', 'owner', 'status',
                    'primer', 'payoff_link')
    # TODO: check if this is useful
    # list_editable = ('owner', )
    exclude = ('additional',)
    search_fields = ('client__name', 'client__mt_id', 'city__name',
                     'city__zip', 'ext_id', 'address',)

    change_actions = ('new_comment', 'new_attachment', 'new_material',
                      'new_workitem')
    inlines = (AttachmentInline, MaterialInline, WorkItemInline,
               TicketEventInline, HistoryInline)
    ordering = ('created_at',)
    fields = ['ext_id', 'client', 'ticket_types', 'city', 'address',
              'client_phone', 'owner', 'status', 'created_at',
              'payoff']
    readonly_fields = ('client_phone', 'full_address')
    exclude = ['additional', 'created_by']

    # =========================================================================
    # METHOD OVERRIDES
    # =========================================================================

    def _hide_icons(self, form, fields, show_add=False, show_edit=False):
        for field in fields:
            form.base_fields[field].widget.can_add_related = show_add
            form.base_fields[field].widget.can_change_related = show_edit

    def get_form(self, request, obj=None, **kwargs):
        if obj:
            self.fields = [f for f in self.fields
                           if f not in ('city', 'address')]
            self.fields.insert(2, 'full_address')
        form = super(TicketAdmin, self).get_form(request, obj, **kwargs)
        if obj:
            self._hide_icons(form, ('owner',))
            self._hide_icons(form, ('payoff',), show_add=True)
        return form

    def get_changelist(self, request, **kwargs):
        return SpecialOrderingChangeList

    def changelist_view(self, request, extra_context=None):
        """
        We need to remove the links to the client and the payoff if the user
        is not an admin
        """
        response = super(TicketAdmin, self).changelist_view(request,
                                                            extra_context)
        if not is_site_admin(request.user):
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
        if is_site_admin(request.user) or \
                obj.status in (u'Kiadva', u'Folyamatban'):
            return ('new_attachment', 'new_material', 'new_workitem',
                    'new_comment',)
        else:
            return ('new_comment',)

    def get_list_filter(self, request):
        if hasattr(request, 'user'):
            if is_site_admin(request.user):
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
            if is_site_admin(request.user):
                return qs
            return qs.filter(owner=request.user)
        return qs

    def get_readonly_fields(self, request, obj=None):
        fields = ('created_by', 'created_at', 'ext_id', 'client',
                  'ticket_types',)
        fields += (self.readonly_fields or tuple())
        if not is_site_admin(request.user):
            fields += ('owner', 'payoff')
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

    def full_address(self, obj):
        return u'{} {}, {}'.format(obj.city.zip, obj.city.name,
                                   obj.address)

    full_address.short_description = u'Cím'

    def client_name(self, obj):
        return obj.client.name

    client_name.short_description = u'Ügyfél neve'

    def client_phone(self, obj):
        return obj.client.phone

    client_phone.short_description = u'Telefonszám'

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

    def ticket_type(self, obj):
        types = ' / '.join([t.name for t in obj.ticket_types.all()])
        return types[:25].strip() + u'...' if len(types) > 25 else types

    ticket_type.short_description = u'Tipus'
    # ticket_type.admin_order_field = ('created_at')

    def new_comment(self, request, obj):
        returnto_tab = self.inlines.index(TicketEventInline)
        return redirect('/admin/rovidtav/ticketevent/add/?event=Megj&ticket={}'
                        '&next=/admin/rovidtav/ticket/{}/change/#/tab/'
                        'inline_{}/'.format(obj.pk, obj.pk, returnto_tab))

    new_comment.label = u'Megjegyzés'
    new_comment.css_class = 'addlink'

    def new_attachment(self, request, obj):
        returnto_tab = self.inlines.index(AttachmentInline)
        return redirect('/admin/rovidtav/attachment/add/?ticket={}&next='
                        '/admin/rovidtav/ticket/{}/change/#/tab/inline_{}/'
                        ''.format(obj.pk, obj.pk, returnto_tab))

    new_attachment.label = u'File'
    new_attachment.css_class = 'addlink'

    def new_material(self, request, obj):
        returnto_tab = self.inlines.index(MaterialInline)
        return redirect('/admin/rovidtav/ticketmaterial/add/?ticket={}&next='
                        '/admin/rovidtav/ticket/{}/change/#/tab/inline_{}/'
                        ''.format(obj.pk, obj.pk, returnto_tab))

    new_material.label = u'Anyag'
    new_material.css_class = 'addlink'

    def new_workitem(self, request, obj):
        returnto_tab = self.inlines.index(WorkItemInline)
        return redirect('/admin/rovidtav/ticketworkitem/add/?ticket={}&next='
                        '/admin/rovidtav/ticket/{}/change/#/tab/inline_{}/'
                        ''.format(obj.pk, obj.pk, returnto_tab))

    new_workitem.label = u'Munka'
    new_workitem.css_class = 'addlink'


admin.site.register(Attachment, AttachmentAdmin)
admin.site.register(City, CityAdmin)
admin.site.register(Payoff, PayoffAdmin)
admin.site.register(Client, ClientAdmin)
admin.site.register(Device, DeviceAdmin)
admin.site.register(DeviceType)
admin.site.register(Ticket, TicketAdmin)
admin.site.register(TicketEvent, TicketEventAdmin)
admin.site.register(TicketType)
admin.site.register(MaterialCategory)
admin.site.register(Material, MaterialAdmin)
admin.site.register(TicketMaterial, TicketMaterialAdmin)
admin.site.register(WorkItem)
admin.site.register(Engineer)
admin.site.register(TicketWorkItem, TicketWorkItemAdmin)
