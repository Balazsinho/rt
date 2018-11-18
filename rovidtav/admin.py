# -*- coding: utf-8 -*-

import os
from copy import copy
from PIL import Image
import StringIO
import zipfile
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pytz

from unidecode import unidecode
from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.sites import AdminSite
# from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.http.response import HttpResponse
from django.template.loader import render_to_string
from django.shortcuts import redirect, render

from rovidtav import settings

from inline_actions.admin import InlineActionsModelAdminMixin
from rovidtav.admin_helpers import ModelAdminRedirect, is_site_admin,\
    CustomDjangoObjectActions, HideIcons, SpecialOrderingChangeList,\
    DeviceOwnerListFilter, get_unread_messages_count,\
    get_unread_messages, send_assign_mail, ContentTypes, create_warehouses
from rovidtav.admin_inlines import AttachmentInline, DeviceInline, NoteInline,\
    TicketInline, HistoryInline, MaterialInline, WorkItemInline,\
    TicketDeviceInline, SystemEmailInline, NTAttachmentInline, MMDeviceInline,\
    NetworkMaterialInline, NetworkWorkItemInline, PayoffTicketInline,\
    MMMaterialInline, MMAttachmentInline, WarehouseMaterialInline,\
    WarehouseDeviceInline, MMMaterialReadonlyInline, WarehouseLocationInline
from rovidtav.models import Attachment, City, Client, Device, DeviceType,\
    Ticket, Note, TicketType, MaterialCategory, Material, TicketMaterial,\
    WorkItem, TicketWorkItem, Payoff, NetworkTicket, NTAttachment,\
    SystemEmail, ApplicantAttributes, DeviceOwner, Tag, Const,\
    NetworkTicketMaterial, NetworkTicketWorkItem, MaterialMovement,\
    MaterialMovementMaterial, Warehouse, WarehouseMaterial, MMAttachment,\
    DeviceReassignEvent, WarehouseLocation
from rovidtav.forms import AttachmentForm, NoteForm, TicketMaterialForm,\
    TicketWorkItemForm, DeviceOwnerForm, TicketForm, TicketTypeForm,\
    NetworkTicketWorkItemForm, NetworkTicketMaterialForm, PayoffForm,\
    WorkItemForm, MaterialForm, MMAttachmentForm, MMMaterialForm,\
    DeviceReassignEventForm, WarehouseLocationForm
from rovidtav.filters import OwnerFilter, IsClosedFilter, NetworkOwnerFilter,\
    PayoffFilter
from django.db.utils import OperationalError

# ============================================================================
# MODELADMIN CLASSSES
# ============================================================================


class HideOnAdmin(admin.ModelAdmin):

    def get_model_perms(self, request):
        # Hide from admin index
        return {}


class CustomUserAdmin(UserAdmin):

    list_display = ('username', 'email', 'phone_number',
                    'first_name', 'last_name',)

    def phone_number(self, obj):
        attrs = ApplicantAttributes.objects.get(user=obj)
        if attrs and attrs.tel_num:
            return attrs.tel_num
        else:
            return None

    phone_number.short_description = u'Telefonszám'


class AttachmentAdmin(HideOnAdmin, ModelAdminRedirect):

    form = AttachmentForm

    def save_model(self, request, obj, form, change):
        super(AttachmentAdmin, self).save_model(request, obj, form, change)
        if obj.is_image() and not obj.name.lower().startswith('imdb'):
            temp_buff = StringIO.StringIO()
            temp_buff.write(obj.data)
            temp_buff.seek(0)

            img = Image.open(temp_buff)
            pixels = settings.IMAGE_DOWNSCALE_PX
            img.thumbnail((pixels, pixels), Image.ANTIALIAS)
            temp_buff = StringIO.StringIO()
            temp_buff.name = obj.name
            img.save(temp_buff, exif=img.info.get('exif', b''))
            temp_buff.seek(0)

            obj._data = temp_buff.read()
            obj.save()
            try:
                obj.ticket.refresh_has_images()
            except AttributeError:
                # We're not maintaining the boolean for having images
                pass


class MMAttachmentAdmin(AttachmentAdmin):

    form = MMAttachmentForm


class MMMaterialAdmin(ModelAdminRedirect, HideOnAdmin):

    form = MMMaterialForm
    change_form_template = os.path.join('rovidtav', 'select2_wide.html')


class PayoffAdmin(admin.ModelAdmin):

    list_display = ('full_name', 'remark')
    inlines = (PayoffTicketInline,)
    form = PayoffForm
    ordering = ('-year', '-month', '-name')

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super(PayoffAdmin, self).get_inline_instances(request, obj=None)

    def full_name(self, obj):
        return unicode(obj)


class CityAdmin(HideOnAdmin, admin.ModelAdmin):

    list_display = ('name', 'zip', 'primer', 'onuk')


class WarehouseMaterialAdmin(HideOnAdmin, admin.ModelAdmin):

    pass


class WarehouseLocationAdmin(HideOnAdmin, ModelAdminRedirect):

    form = WarehouseLocationForm


class TagAdmin(HideOnAdmin, admin.ModelAdmin):

    list_display = ('name', 'remark')


class DeviceOwnerAdmin(CustomDjangoObjectActions, HideOnAdmin,
                       ModelAdminRedirect, HideIcons):

    hide_add = True
    form = DeviceOwnerForm
    change_form_template = os.path.join('rovidtav', 'select2_wide.html')

    def get_form(self, request, obj=None, **kwargs):
        form = super(DeviceOwnerAdmin, self).get_form(request, obj, **kwargs)
        self._hide_icons(form, ('device',))
        ticket_id = request.GET.get('ticket_id')
        user = request.user
        if ticket_id:
            ticket = Ticket.objects.get(id=int(ticket_id))
            user = ticket.owner or request.user
        try:
            warehouse = Warehouse.objects.get(owner=user)
            allowed_pks = DeviceOwner.objects.filter(
                content_type=ContentTypes.warehouse, object_id=warehouse.id).values_list('device__id', flat=True)
            devices = Device.objects.filter(id__in=allowed_pks, returned_at__isnull=True)
            form.base_fields['device'].queryset = devices
        except Warehouse.DoesNotExist:
            pass
        return form


class DeviceAdmin(CustomDjangoObjectActions,
                  ModelAdminRedirect, HideIcons):

    list_display = ('sn', 'device_type', 'owner_link', 'returned_at')
    search_fields = ('type__name', 'sn')
    list_filter = (DeviceOwnerListFilter,)
    change_actions = ('new_note',)
    readonly_fields = ('returned_at',)

    inlines = (NoteInline, HistoryInline)

    change_form_template = os.path.join('rovidtav', 'select2_wide.html')
    change_list_template = os.path.join('rovidtav', 'change_list_noadd.html')

    def get_queryset(self, request):
        if request.user.is_superuser:
            return ModelAdminRedirect.get_queryset(self, request)
        wh = Warehouse.objects.get(owner=request.user.id)
        pks = DeviceOwner.objects.filter(
            content_type=ContentTypes.warehouse,
            object_id=wh.id).values_list('id', flat=True)
        return Device.objects.filter(id__in=pks)

    def device_type(self, obj):
        if obj.type:
            return obj.type.name

    device_type.short_description = u'Típus'

    def owner_link(self, obj):
        if obj.owner:
            if isinstance(obj.owner.owner, Client):
                return (u'<a href="/admin/rovidtav/client/{}/change">{}</a>'
                        u''.format(obj.owner.owner.pk, unicode(obj.owner.owner)))
            else:
                return obj.owner.owner

    owner_link.allow_tags = True
    owner_link.short_description = u'Tulajdonos'

    def new_note(self, request, obj):
        returnto_tab = self.inlines.index(NoteInline)
        return redirect('/admin/rovidtav/note/add/?content_type={}&object_id='
                        '{}&next=/admin/rovidtav/device/{}/change/#/tab/'
                        'inline_{}/'.format(obj.get_content_type(),
                                            obj.pk, obj.pk, returnto_tab))

    new_note.label = u'Megjegyzés'
    new_note.css_class = 'addlink'

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super(DeviceAdmin, self).get_inline_instances(request, obj=None)


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

    def get_model_perms(self, request):
        if not is_site_admin(request.user):
            return {}
        else:
            return super(ClientAdmin, self).get_model_perms(request)


class SystemEmailAdmin(admin.ModelAdmin):

    list_display = ('status', 'related_ticket', 'remark', 'created_by',
                    'created_at')
    list_filter = ('status', )

    def related_ticket(self, obj):
        rel_id = obj.content_object.pk
        return (u'<a href="/admin/rovidtav/ticket/{}/change">{}</a>'
                u''.format(rel_id, obj.content_object.ext_id))

    related_ticket.allow_tags = True
    related_ticket.short_description = u'Jegy'

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class MaterialAdmin(admin.ModelAdmin):

    list_display = ('sn', 'name', 'category', 'price', 'unit', 'comes_from',
                    'tech_display')
    search_fields = ('sn', 'name', 'category__name')
    list_filter = ('category__name', )
    form = MaterialForm

    def tech_display(self, obj):
        tech_dict = dict([(str(t[0]), t[1]) for t in Const.get_tech_choices()])
        if obj.technologies:
            return u', '.join([tech_dict[t] for t in obj.technologies])
        else:
            return u''

    tech_display.short_description = u'Technológia'


class TicketMaterialAdmin(HideOnAdmin, ModelAdminRedirect):

    form = TicketMaterialForm
    change_form_template = os.path.join('rovidtav', 'select2_wide.html')


class NetworkTicketMaterialAdmin(HideOnAdmin, ModelAdminRedirect):

    form = NetworkTicketMaterialForm
    change_form_template = os.path.join('rovidtav', 'select2_wide.html')


class WorkItemAdmin(admin.ModelAdmin):

    form = WorkItemForm

    list_display = ('art_number', 'name', 'art_price', 'bulk_price',
                    'given_price', 'tech_display')

    def tech_display(self, obj):
        tech_dict = dict([(str(t[0]), t[1]) for t in Const.get_tech_choices()])
        if obj.technologies:
            return u', '.join([tech_dict[t] for t in obj.technologies])
        else:
            return u''

    tech_display.short_description = u'Technológia'


class DeviceTypeAdmin(HideOnAdmin, admin.ModelAdmin):

    list_display = ('name', 'technology', 'sn_pattern')
    ordering = ('name',)


class TicketWorkItemAdmin(HideOnAdmin, ModelAdminRedirect):

    form = TicketWorkItemForm
    change_form_template = os.path.join('rovidtav', 'select2_wide.html')


class NetworkTicketWorkItemAdmin(HideOnAdmin, ModelAdminRedirect):

    form = NetworkTicketWorkItemForm
    change_form_template = os.path.join('rovidtav', 'select2_wide.html')


class NoteAdmin(HideOnAdmin, ModelAdminRedirect):

    form = NoteForm


class MaterialCategoryAdmin(HideOnAdmin, admin.ModelAdmin):

    pass


class TicketTypeAdmin(HideOnAdmin, admin.ModelAdmin):

    form = TicketTypeForm


class DeviceReassignEventAdmin(HideOnAdmin, ModelAdminRedirect,
                               admin.ModelAdmin):

    form = DeviceReassignEventForm

# =============================================================================
# ADMIN PAGES
# =============================================================================


class MaterialMovementAdmin(CustomDjangoObjectActions,
                            InlineActionsModelAdminMixin,
                            admin.ModelAdmin):
    list_per_page = 200
    list_display_links = None
    list_display = ('from_to', 'mm_link', 'created', 'materials_count',
                    'devices_count', 'fin_icon')
    list_filter = ('source', 'target', 'finalized')

    inlines = [MMMaterialInline, MMDeviceInline, MMAttachmentInline,
               NoteInline]
    change_actions = ['finalize', 'new_material', 'new_device',
                      'new_attachment', 'new_note']
    add_form_template = os.path.join('rovidtav', 'select2.html')
    fields = ['source', 'target', 'created_at', 'delivery_num']

    def has_delete_permission(self, request, obj=None):
        return False

    def get_changelist(self, request, **kwargs):
        create_warehouses()
        return admin.ModelAdmin.get_changelist(self, request, **kwargs)

    def get_actions(self, request):
        actions = super(MaterialMovementAdmin, self).get_actions(request)
        del actions['delete_selected']
        return actions

    def get_change_actions(self, request, object_id, form_url):
        if not object_id:
            return []
        mm = MaterialMovement.objects.get(id=object_id)
        if not mm.finalized:
            actions = ['finalize']
        else:
            actions = []
        if is_site_admin(request.user) and not mm.finalized:
            actions.extend([act for act in self.change_actions
                            if act not in ('finalize',)])
        else:
            actions.append('new_note')
        return actions

    def get_inline_instances(self, request, obj=None):
        if not obj and not request.path.strip('/').endswith('change'):
            return []
        orig_inlines = copy(self.inlines)
        if obj.finalized:
            self.inlines.remove(MMMaterialInline)
            self.inlines.insert(0, MMMaterialReadonlyInline)
        instances = super(MaterialMovementAdmin, self).get_inline_instances(request, obj=None)
        self.inlines = orig_inlines
        return instances

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.finalized:
            return ['created_at', 'source', 'target', 'delivery_num']
        else:
            return ['delivery_num']

    def new_note(self, request, obj):
        return redirect('/admin/rovidtav/note/add/?content_type={}&object_id='
                        '{}&next={}'.format(obj.get_content_type(),
                                            obj.pk,
                                            self._returnto(obj, NoteInline)))

    new_note.label = u'Megjegyzés'
    new_note.css_class = 'addlink'

    def new_attachment(self, request, obj):
        return redirect('/admin/rovidtav/mmattachment/add/?materialmovement'
                        '={}&next={}'.format(
                            obj.pk, self._returnto(obj, MMAttachmentInline)))

    new_attachment.label = u'File'
    new_attachment.css_class = 'addlink'

    def new_material(self, request, obj):
        return redirect('/admin/rovidtav/materialmovementmaterial/add/?'
                        'materialmovement={}&next={}'
                        ''.format(obj.pk, self._returnto(obj, MMMaterialInline)))

    new_material.label = u'Anyag'
    new_material.css_class = 'addlink'

    def new_device(self, request, obj):
        return redirect('/admin/rovidtav/devicereassignevent/add/?materialmovement={}&next={}'
                        ''.format(obj.pk, self._returnto(obj, MMDeviceInline)))

    new_device.label = u'Eszköz'
    new_device.css_class = 'addlink'

    def finalize(self, request, obj):

        def _substract(warehouse, movement):
            for material in WarehouseMaterial.objects.filter(
                    material=movement.material, warehouse=warehouse):
                if movement.amount < material.amount:
                    material.amount -= movement.amount
                    material.save()
                elif material.amount < movement.amount:
                    # add message ?
                    material.delete()
                else:
                    material.delete()

        for movement in MaterialMovementMaterial.objects.filter(materialmovement=obj):
            # Substract from source
            try:
                _substract(obj.source, movement)
            except WarehouseMaterial.DoesNotExist:
                # add message
                pass
            except WarehouseMaterial.MultipleObjectsReturned:
                # merge them and add message and substract
                pass

            # Add to target
            try:
                material = WarehouseMaterial.objects.get(
                    material=movement.material, warehouse=obj.target)
                material.amount += movement.amount
                if movement.location_to:
                    material.location = movement.location_to
                material.save()
            except WarehouseMaterial.DoesNotExist:
                WarehouseMaterial.objects.create(material=movement.material,
                                                 warehouse=obj.target,
                                                 amount=movement.amount,
                                                 created_by=request.user,
                                                 location=movement.location_to)

        for dre in DeviceReassignEvent.objects.filter(materialmovement=obj):
            try:
                device_owner = DeviceOwner.objects.get(device=dre.device)
                device_owner.content_type = ContentTypes.warehouse
                device_owner.object_id = obj.target.id
                device_owner.save(user=request.user)
            except DeviceOwner.DoesNotExist:
                DeviceOwner.objects.create(device=dre.device,
                                           content_type=ContentTypes.warehouse,
                                           object_id=obj.target.id)

        obj.finalized = True
        obj.save()
        messages.add_message(request, messages.INFO, u'{} véglegesítve'.format(obj.delivery_num))
        return redirect('/admin/rovidtav/materialmovement')

    finalize.label = u'Véglegesít'
    finalize.onclick = u"return confirm('Biztos?')"
    finalize.allow_tags = True

    def _returnto(self, obj, inline):
        returnto_tab = self.inlines.index(inline)
        return ('/admin/rovidtav/materialmovement/{}/change/#/tab/inline_{}/'
                ''.format(obj.pk, returnto_tab))

    # =========================================================================
    # FIELDS
    # =========================================================================

    def from_to(self, obj):
        return (u'{} <img style="width: 15px; height: 10px" src="/static/images'
                u'/arrow_in.png" /> {}'.format(obj.source, obj.target))

    from_to.allow_tags = True
    from_to.short_description = u'Irány'

    def created(self, obj):
        return u'{} - {}'.format(obj.created_by, obj.created_at.strftime('%Y-%m-%d'))

    created.short_description = u'Rögzítette'

    def materials_count(self, obj):
        return MaterialMovementMaterial.objects.filter(materialmovement=obj).count()

    materials_count.short_description = u'Anyagok'

    def devices_count(self, obj):
        return DeviceReassignEvent.objects.filter(materialmovement=obj).count()

    devices_count.short_description = u'Eszközök'

    def mm_link(self, obj):
        return (u'<a href="/admin/rovidtav/materialmovement/{}/change#/tab/inline_0/">'
                u'{}</a>'.format(obj.pk, obj.delivery_num))

    mm_link.allow_tags = True
    mm_link.short_description = u'Szállító száma'

    def fin_icon(self, obj):
        if obj.finalized:
            return u'<span style="color: #03A101">&#10003;</span>'
        else:
            return u'<span style="color: #A10101">&#10007;</span>'

    fin_icon.allow_tags = True
    fin_icon.short_description = u'Véglegesítve'


class WarehouseAdmin(CustomDjangoObjectActions,
                     InlineActionsModelAdminMixin,
                     admin.ModelAdmin):

    inlines = [WarehouseMaterialInline, NoteInline, WarehouseDeviceInline,
               WarehouseLocationInline]
    list_display = ['warehouse_name', 'num_devices', 'num_materials']
    fields = ['name', 'city', 'address']
    change_actions = ['new_note', 'new_location']
    ordering = ['owner__last_name', 'owner__first_name', 'name']

    def __init__(self, model, admin_site):
        admin.ModelAdmin.__init__(self, model, admin_site)
        self.deviceowner_ct = ContentTypes.deviceowner

    def get_changelist(self, request, **kwargs):
        create_warehouses()
        return admin.ModelAdmin.get_changelist(self, request, **kwargs)

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super(WarehouseAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def get_readonly_fields(self, request, obj=None):
        if obj:
            fields = ('name', 'city', 'address')
        else:
            fields = ()
        fields += (self.readonly_fields or tuple())
        return fields

    def get_inline_instances(self, request, obj=None):
        if not obj and not request.path.strip('/').endswith('change'):
            return []
        return super(WarehouseAdmin, self).get_inline_instances(request, obj)

    def new_note(self, request, obj):
        return redirect('/admin/rovidtav/note/add/?content_type={}&object_id='
                        '{}&next={}'.format(obj.get_content_type(),
                                            obj.pk,
                                            self._returnto(obj, NoteInline)))

    new_note.label = u'Megjegyzés'
    new_note.css_class = 'addlink'

    def new_location(self, request, obj):
        return redirect('/admin/rovidtav/warehouselocation/add/?warehouse='
                        '{}&next={}'.format(
                            obj.pk,
                            self._returnto(obj, WarehouseLocationInline)))

    new_location.label = u'Raktár hely'
    new_location.css_class = 'addlink'

    def _returnto(self, obj, inline):
        returnto_tab = self.inlines.index(inline)
        return ('/admin/rovidtav/warehouse/{}/change/#/tab/inline_{}/'
                ''.format(obj.pk, returnto_tab))

    def warehouse_name(self, obj):
        if obj.owner:
            return obj.name
        return u'Raktár - {} ({})'.format(obj.name, obj.city.name)

    warehouse_name.short_description = u''

    def num_devices(self, obj):
        return DeviceOwner.objects.filter(
            content_type=ContentTypes.warehouse, object_id=obj.id).count()

    num_devices.short_description = u'Eszközök'

    def num_materials(self, obj):
        return WarehouseMaterial.objects.filter(warehouse=obj).count()

    num_materials.short_description = u'Anyagok'


class TicketAdmin(CustomDjangoObjectActions,
                  InlineActionsModelAdminMixin,
                  admin.ModelAdmin,
                  HideIcons):

    # =========================================================================
    # PARAMETERS
    # =========================================================================
    form = TicketForm
    add_form_template = os.path.join('rovidtav', 'select2.html')
    # change_form_template = os.path.join('admin',
    #                                    'two_column_change_form.html')

    list_per_page = 200
    list_display_links = None
    list_display = ('ext_id_link', 'address', 'city_name', 'client_name',
                    # 'client_link',
                    'ticket_type', 'created_at_fmt',
                    'closed_at_fmt', 'owner', 'status', 'agreed_time_fmt',
                    'primer', 'has_images_nice', 'collectable', 'remark',
                    'payoff_link', 'ticket_tags_nice')
    # TODO: check if this is useful
    # list_editable = ('owner', )
    search_fields = ('client__name', 'client__mt_id', 'city__name',
                     'city__zip', 'ext_id', 'address', 'remark')
    change_actions = ('new_note', 'new_attachment', 'new_material',
                      'new_device', 'new_workitem', 'download_html')
    changelist_actions = ('summary_list',)
    inlines = (NoteInline, AttachmentInline, MaterialInline,
               WorkItemInline, TicketDeviceInline, SystemEmailInline)
    ordering = ('-created_at',)
    fields = ['ext_id', 'client', 'ticket_types', 'city', 'address',
              'client_phone', 'owner', 'status', 'closed_at',
              'agreed_time_from', 'agreed_time_to',
              'remark', 'ticket_tags', 'payoffs', 'collectable', 'created_at', ]
    readonly_fields = ('client_phone', 'full_address', 'collectable',
                       'agreed_time_from', 'agreed_time_to')
    exclude = ['additional', 'created_by']
    actions = ['download_action']

    class Media:
        css = {
            'all': ('css/ticket.css',)
        }
        js = ('js/ticket_list.js',)

    # =========================================================================
    # METHOD OVERRIDES
    # =========================================================================

    def get_form(self, request, obj=None, **kwargs):
        form = super(TicketAdmin, self).get_form(request, obj, **kwargs)
        if obj and is_site_admin(request.user):
            self._hide_icons(form, ('payoffs',), show_add=True)
            self._hide_icons(form, ('owner',))
        return form

    def get_changelist(self, request, **kwargs):
        return SpecialOrderingChangeList

    def changeform_view(self, request, object_id=None, form_url='',
                        extra_context=None):
        extra_context = extra_context or {}
        extra_context['siteSpecificContext'] = {
            'closed_statuses': [Const.TicketStatus.DONE_SUCC,
                                Const.TicketStatus.DONE_UNSUCC,
                                Const.TicketStatus.DUPLICATE]
        }
        extra_context['hideSaveOnTabs'] = 'true'

        return InlineActionsModelAdminMixin.changeform_view(self, request, object_id=object_id, form_url=form_url, extra_context=extra_context)

    def changelist_view(self, request, extra_context=None):
        """
        We need to remove the links to the client and the payoff if the user
        is not an admin
        """
        response = super(TicketAdmin, self).changelist_view(request,
                                                            extra_context)
        if not is_site_admin(request.user):
            subst = {'client_link': 'client_mt_id',
                     }
            exclude = ['payoff_link']
            columns = response.context_data['cl'].list_display
            new_cols = [subst.get(c, c) for c in columns if c not in exclude]
            response.context_data['cl'].list_display = new_cols
        return response

    def get_actions(self, request):
        actions = super(TicketAdmin, self).get_actions(request)
        del actions['delete_selected']
        return actions

    def download_action(self, request, queryset):
        temp = StringIO.StringIO()
        with zipfile.ZipFile(temp, 'w') as archive:
            for ticket in queryset:
                attachments = []
                for att in Attachment.objects.filter(ticket=ticket):
                    if att.is_image() and not att.name.lower().startswith('imdb'):
                        attachments.append(att)
                for att in attachments:
                    archive.writestr('{}/{}'.format(ticket.ext_id, unidecode(att.name)),
                                     att.data)

        temp.seek(0)
        response = HttpResponse(temp,
                                content_type='application/force-download')
        fname = datetime.datetime.now().strftime('jegyek_%y%m%d%H%M.zip')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(fname)
        return response

    download_action.short_description = u'Letöltés ZIP-ben'

    def get_change_actions(self, request, object_id, form_url):
        obj = Ticket.objects.get(pk=object_id)
        if is_site_admin(request.user) or \
                obj.status in (u'Kiadva', u'Folyamatban'):
            actions = ('new_note', 'new_attachment',
                       'new_material', 'new_workitem',
                       'new_device')
            if obj.is_install_ticket():
                actions += ('download_html',)
            return actions
        else:
            return ('new_note',)

    def get_list_filter(self, request):
        if hasattr(request, 'user'):
            if is_site_admin(request.user):
                return (
                        'city__primer', OwnerFilter, IsClosedFilter,
                        'has_images', 'ticket_tags', PayoffFilter,
                        )
            else:
                return (IsClosedFilter,)

    def lookup_allowed(self, key, value):
        if key in ('city__primer'):
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
        if obj:
            fields = ('created_by', 'created_at', 'ext_id', 'client',
                      'ticket_types', 'city', 'address')
        else:
            fields = ()
        fields += (self.readonly_fields or tuple())
        if not is_site_admin(request.user):
            fields += ('owner', 'payoffs', 'remark', 'ticket_tags')
            if obj.status not in (u'Kiadva', u'Folyamatban'):
                fields += ('status', 'closed_at')
        return fields

    def get_inline_instances(self, request, obj=None):
        if not obj and not request.path.strip('/').endswith('change'):
            return []
        orig_inlines = self.inlines
        if not is_site_admin(request.user):
            # Remove the email inline if not an admin
            self.inlines = [i for i in self.inlines
                            if i not in (SystemEmailInline, )]
        inline_inst = super(TicketAdmin, self).get_inline_instances(request,
                                                                    obj=None)
        self.inlines = orig_inlines
        return inline_inst

    def save_model(self, request, obj, form, change):
        """
        Saves the model and handles notifications if needed
        """
        notify = obj.save()
        if notify and obj.owner and obj.owner.email:
            try:
                ticket_html = Attachment.objects.get(ticket=obj,
                                                     name='Hibajegy.html')
            except Attachment.DoesNotExist:
                ticket_html = None
            ticket_url = ('{}/admin/rovidtav/ticket/{}'
                          ''.format(settings.SELF_URL, obj.pk))

            ctx = {'ticket_url': ticket_url,
                   'ticket_html': ticket_html.data if ticket_html else ''}

            msg = MIMEMultipart('alternative')
            msg['Subject'] = u'Új jegy - {} {} - Task Nr: {}'.format(
                obj.city.name, obj.address, obj.ext_id)
            msg['From'] = settings.EMAIL_SENDER
            msg['To'] = obj.owner.email
            plain_template = render_to_string('assign_notification.txt',
                                              context={'ticket': obj})
            html_template = render_to_string('assign_notification.html',
                                             context=ctx)
            part1 = MIMEText(plain_template, 'plain', 'utf-8')
            part2 = MIMEText(html_template, 'html', 'utf-8')

            msg.attach(part1)
            msg.attach(part2)

            send_assign_mail(msg, obj)

    # =========================================================================
    # FIELDS
    # =========================================================================

    def collectable(self, obj):
        return obj[Ticket.Keys.COLLECTABLE_MONEY] or '-'

    collectable.short_description = u'Beszed.'

    def payoff_link(self, obj):
        payoffs = []
        if obj.payoffs:
            for payoff in obj.payoffs.all():
                payoff_a = (u'<a href="/admin/rovidtav/payoff/{}/change">{}'
                            u'</a>'.format(payoff.pk, unicode(payoff)))
                payoffs.append(payoff_a)
            return u',&nbsp'.join(payoffs)
        else:
            return None

    payoff_link.allow_tags = True
    payoff_link.short_description = u'Elszám.'

    def ext_id_link(self, obj):
        return (u'<a href="/admin/rovidtav/ticket/{}/change#/tab/inline_0/">'
                u'{}</a>'.format(obj.pk, obj.ext_id))

    ext_id_link.allow_tags = True
    ext_id_link.short_description = u'Jegy ID'

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
    client_name.admin_order_field = 'client__name'

    def client_phone(self, obj):
        return obj.client.phone

    client_phone.short_description = u'Telefonszám'

    def primer(self, obj):
        return obj.city.primer

    primer.short_description = u'Primer'
    primer.admin_order_field = 'city__primer'

    def city_name(self, obj):
        return u'{} {}'.format(obj.city.name, obj.city.zip)

    city_name.short_description = u'Település'
    city_name.admin_order_field = 'city__name'

    def created_at_fmt(self, obj):
        # return obj.created_at.strftime('%Y.%m.%d %H:%M')
        return obj.created_at.strftime('%Y.%m.%d')

    created_at_fmt.short_description = u'Rögz.'
    created_at_fmt.admin_order_field = ('created_at')

    def agreed_time_fmt(self, obj):
        # return obj.created_at.strftime('%Y.%m.%d %H:%M')
        result = None
        if obj.agreed_time_from:
            result = obj.agreed_time_from.astimezone(pytz.timezone("Europe/Budapest")).strftime('%m.%d %H')
        if obj.agreed_time_to:
            result += '-' + obj.agreed_time_to.astimezone(pytz.timezone("Europe/Budapest")).strftime('%H')
        return result

    agreed_time_fmt.short_description = u'Egyzt. idő'
    agreed_time_fmt.admin_order_field = ('agreed_time_from')

    def closed_at_fmt(self, obj):
        # return obj.created_at.strftime('%Y.%m.%d %H:%M')
        return obj.closed_at.strftime('%Y.%m.%d') if obj.closed_at else None

    closed_at_fmt.short_description = u'Lezárva'
    closed_at_fmt.admin_order_field = ('closed_at')

    def ticket_type(self, obj):
        types = ' / '.join([t.name for t in obj.ticket_types.all()])
        return types[:25].strip() + u'...' if len(types) > 25 else types

    ticket_type.short_description = u'Tipus'
    # ticket_type.admin_order_field = ('created_at')

    def has_images_nice(self, obj):
        return u'✓' if obj.has_images else ''

    has_images_nice.short_description = u'Kép'

    def ticket_tags_nice(self, obj):
        return ', '.join([t.name for t in obj.ticket_tags.all()])

    ticket_tags_nice.short_description = u'Cimkék'

    # =========================================================================
    # ACTIONS
    # =========================================================================

    def summary_list(self, request, obj):
        return redirect('/reports/osszesito')

    summary_list.label = u'Összesítő lista'
    # summary_list.css_class = 'addlink'

    def new_note(self, request, obj):
        return redirect('/admin/rovidtav/note/add/?content_type={}&object_id='
                        '{}&next={}'.format(obj.get_content_type(),
                                            obj.pk,
                                            self._returnto(obj, NoteInline)))

    new_note.label = u'Megjegyzés'
    new_note.css_class = 'addlink'

    def new_attachment(self, request, obj):
        return redirect('/admin/rovidtav/attachment/add/?ticket={}&next={}'
                        ''.format(obj.pk,
                                  self._returnto(obj, AttachmentInline)))

    new_attachment.label = u'File'
    new_attachment.css_class = 'addlink'

    def new_material(self, request, obj):
        return redirect('/admin/rovidtav/ticketmaterial/add/?ticket={}&next={}'
                        ''.format(obj.pk, self._returnto(obj, MaterialInline)))

    new_material.label = u'Anyag'
    new_material.css_class = 'addlink'

    def new_workitem(self, request, obj):
        return redirect('/admin/rovidtav/ticketworkitem/add/?ticket={}&next={}'
                        ''.format(obj.pk, self._returnto(obj, WorkItemInline)))

    new_workitem.label = u'Munka'
    new_workitem.css_class = 'addlink'

    def new_device(self, request, obj):
        return redirect('/admin/rovidtav/deviceowner/add/?content_type={}'
                        '&object_id={}&ticket_id={}&next={}'
                        ''.format(obj.client.get_content_type(), obj.client.pk,
                                  obj.pk,
                                  self._returnto(obj, TicketDeviceInline)))

    new_device.label = u'Eszköz'
    new_device.css_class = 'addlink'

    def _returnto(self, obj, inline):
        returnto_tab = self.inlines.index(inline)
        return ('/admin/rovidtav/ticket/{}/change/#/tab/inline_{}/'
                ''.format(obj.pk, returnto_tab))

    def download_html(self, request, ticket):
        try:
            map_img = Attachment.objects.get(ticket=ticket,
                                             name__istartswith='imdb')
            map_img = map_img._data
        except Attachment.DoesNotExist:
            map_img = None

        materials = {}
        for material_sn in ('40292016', '40296137', '40299501', '40306778',
                            '40296139', '40292261'):
            try:
                material = Material.objects.get(sn=material_sn)
            except Material.DoesNotExist:
                continue

            try:
                tm = TicketMaterial.objects.get(ticket=ticket,
                                                material=material)
                materials[material_sn] = tm.amount
            except TicketMaterial.DoesNotExist:
                continue

        ctx = {'wfms_id': ticket.ext_id,
               'client_name': ticket.client.name,
               'city_primer': ticket.city.primer or '',
               'city_name': ticket.city.name,
               'city_zip': ticket.city.zip,
               'owner_name': u'{} {}'.format(ticket.owner.last_name,
                                             ticket.owner.first_name)
               if ticket.owner else '',
               'client_address': ticket.address,
               'map': map_img,
               'today': datetime.datetime.now().strftime('%Y-%m-%d'),
               'year': datetime.datetime.now().strftime('%Y'),
               'materials': materials,
               }
        response = render(request, 'leltaruj1.html', ctx)
        response.content_type = 'text/html'
        response['Content-Disposition'] = ('attachment; filename=leltar_'
                                           '{}.html'.format(ticket.ext_id))
        return response

    download_html.label = u'Leltár adatlap'
    download_html.css_class = 'downloadlink'


class NetworkTicketAdmin(CustomDjangoObjectActions,
                         InlineActionsModelAdminMixin,
                         admin.ModelAdmin, HideIcons):

    list_per_page = 200
    list_display_links = None
    list_display = ('address_link', 'city_name', 'onu',
                    'ticket_type', 'created_at_fmt',
                    'closed_at_fmt', 'owner_display', 'status',
                    'ticket_tags_nice')
    change_actions = ('new_note', 'new_attachment', 'new_material',
                      'new_workitem',)
    inlines = (NoteInline, NTAttachmentInline, NetworkMaterialInline,
               NetworkWorkItemInline)
    ordering = ('-created_at',)
    search_fields = ('city__name', 'city__zip', 'address',
                     'master_sn')

    fields = ['city', 'address', 'onu', 'master_sn',
              'psu_placement', 'ticket_types',
              'ticket_tags', 'owner', 'status', 'closed_at']
    readonly_fields = ('full_address',)
    list_filter = ('onu', NetworkOwnerFilter, IsClosedFilter, 'ticket_tags')
    actions = ['download_action']

    class Media:
        js = ('js/network_ticket.js',)

    def get_list_filter(self, request):
        if hasattr(request, 'user'):
            if is_site_admin(request.user):
                return self.list_filter
            else:
                return ('onu', IsClosedFilter,)

    def get_readonly_fields(self, request, obj=None):
        fields = self.readonly_fields
        if not is_site_admin(request.user):
            fields += ('owner', 'address', 'ticket_types', 'ticket_tags',
                       'city', 'closed_at', 'onu', 'master_sn',
                       'psu_placement',)
            if obj.status not in (Const.TicketStatus.NEW,
                                  Const.TicketStatus.IN_PROGRESS,
                                  Const.TicketStatus.ASSIGNED):
                fields += ('status',)
        return fields

    def get_actions(self, request):
        actions = super(NetworkTicketAdmin, self).get_actions(request)
        del actions['delete_selected']
        return actions

    def get_form(self, request, obj=None, **kwargs):
        form = super(NetworkTicketAdmin, self).get_form(request, obj, **kwargs)
        if is_site_admin(request.user):
            self._hide_icons(form, ('owner',))
            self._hide_icons(form, ('city',))
        return form

    def get_queryset(self, request):
        qs = super(NetworkTicketAdmin, self).get_queryset(request)
        if hasattr(request, 'user'):
            if is_site_admin(request.user):
                return qs
            return qs.filter(owner__in=[request.user.pk])
        return qs

    def has_delete_permission(self, request, obj=None):
        return False

    def get_inline_instances(self, request, obj=None):
        if not obj and not request.path.split('#')[0].strip('/').endswith('change'):
            return []
        return super(NetworkTicketAdmin, self).get_inline_instances(request,
                                                                    obj)

    def download_action(self, request, queryset):
        temp = StringIO.StringIO()
        with zipfile.ZipFile(temp, 'w') as archive:
            for ticket in queryset:
                attachments = []
                for att in NTAttachment.objects.filter(ticket=ticket):
                    if att.is_image():
                        attachments.append(att)
                for att in attachments:
                    addr = ticket.address.replace(u'/', u'-')
                    archive.writestr(u'{}/{}'.format(addr, att.name), att.data)

        temp.seek(0)
        response = HttpResponse(temp,
                                content_type='application/force-download')
        fname = datetime.datetime.now().strftime('halozat_jegyek_%y%m%d%H%M.zip')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(fname)
        return response

    download_action.short_description = u'Letöltés ZIP-ben'

    def address_link(self, obj):
        return (u'<a href="/admin/rovidtav/networkticket/{}/change#'
                u'/tab/inline_0/">{}</a>'.format(obj.pk, obj.address))

    address_link.allow_tags = True
    address_link.short_description = u'Cím'

    def ticket_type(self, obj):
        types = ' / '.join([t.name for t in obj.ticket_types.all()])
        return types[:25].strip() + u'...' if len(types) > 25 else types

    ticket_type.short_description = u'Tipus'

    def created_at_fmt(self, obj):
        # return obj.created_at.strftime('%Y.%m.%d %H:%M')
        return obj.created_at.strftime('%Y.%m.%d')

    created_at_fmt.short_description = u'Felvéve'
    created_at_fmt.admin_order_field = ('created_at')

    def closed_at_fmt(self, obj):
        # return obj.created_at.strftime('%Y.%m.%d %H:%M')
        return obj.closed_at.strftime('%Y.%m.%d') if obj.closed_at else None

    closed_at_fmt.short_description = u'Lezárva'
    closed_at_fmt.admin_order_field = ('closed_at')

    def ticket_tags_nice(self, obj):
        return ', '.join([t.name for t in obj.ticket_tags.all()])

    ticket_tags_nice.short_description = u'Cimkék'

    def city_name(self, obj):
        return u'{} {}'.format(obj.city.name, obj.city.zip)

    city_name.short_description = u'Település'
    city_name.admin_order_field = 'city__name'

    def full_address(self, obj):
        return u'{} {}, {}'.format(obj.city.zip, obj.city.name,
                                   obj.address)

    full_address.short_description = u'Cím'

    def owner_display(self, obj):
        return u', '.join([u.username for u in obj.owner.all()])

    owner_display.short_description = u'Szerelő'

    # =========================================================================
    # ACTIONS
    # =========================================================================

    def _returnto(self, obj, inline):
        returnto_tab = self.inlines.index(inline)
        return ('/admin/rovidtav/networkticket/{}/change/#/tab/inline_{}/'
                ''.format(obj.pk, returnto_tab))

    def new_note(self, request, obj):
        return redirect('/admin/rovidtav/note/add/?content_type={}&object_id='
                        '{}&next={}'.format(obj.get_content_type(),
                                            obj.pk,
                                            self._returnto(obj, NoteInline)))

    new_note.label = u'Megjegyzés'
    new_note.css_class = 'addlink'

    def new_attachment(self, request, obj):
        return redirect('/admin/rovidtav/ntattachment/add/?ticket={}&next={}'
                        ''.format(obj.pk,
                                  self._returnto(obj, NTAttachmentInline)))

    new_attachment.label = u'File'
    new_attachment.css_class = 'addlink'

    def new_material(self, request, obj):
        return redirect('/admin/rovidtav/networkticketmaterial/add/?ticket={}&next={}'
                        ''.format(obj.pk, self._returnto(obj, NetworkMaterialInline)))

    new_material.label = u'Anyag'
    new_material.css_class = 'addlink'

    def new_workitem(self, request, obj):
        return redirect('/admin/rovidtav/networkticketworkitem/add/?ticket={}&next={}'
                        ''.format(obj.pk, self._returnto(obj, NetworkWorkItemInline)))

    new_workitem.label = u'Munka'
    new_workitem.css_class = 'addlink'


class CustomAdminSite(AdminSite):

    def login(self, request, extra_context=None):
        extra_context = extra_context or {}
        return super(CustomAdminSite, self).login(request, extra_context)

    def each_context(self, request):
        ctx = super(CustomAdminSite, self).each_context(request)
        ctx.update(get_unread_messages_count(request.user))
        ctx.update(get_unread_messages(request.user))
        ctx.update({'c': 'sadf'})
        return ctx


admin.site = CustomAdminSite()

admin.site.register(User, CustomUserAdmin)
admin.site.register(Group)
admin.site.register(SystemEmail, SystemEmailAdmin)

admin.site.register(City, CityAdmin)
admin.site.register(Payoff, PayoffAdmin)
admin.site.register(Client, ClientAdmin)
admin.site.register(TicketType, TicketTypeAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Ticket, TicketAdmin)
admin.site.register(NetworkTicket, NetworkTicketAdmin)
admin.site.register(ApplicantAttributes)
admin.site.register(Note, NoteAdmin)
admin.site.register(Attachment, AttachmentAdmin)
admin.site.register(NTAttachment, AttachmentAdmin)
admin.site.register(NetworkTicketMaterial, NetworkTicketMaterialAdmin)
admin.site.register(NetworkTicketWorkItem, NetworkTicketWorkItemAdmin)

admin.site.register(MaterialMovement, MaterialMovementAdmin)
admin.site.register(MaterialMovementMaterial, MMMaterialAdmin)
admin.site.register(MMAttachment, MMAttachmentAdmin)
admin.site.register(Warehouse, WarehouseAdmin)
admin.site.register(WarehouseLocation, WarehouseLocationAdmin)
admin.site.register(WarehouseMaterial, WarehouseMaterialAdmin)
admin.site.register(DeviceReassignEvent, DeviceReassignEventAdmin)

admin.site.register(WorkItem, WorkItemAdmin)
admin.site.register(TicketWorkItem, TicketWorkItemAdmin)

admin.site.register(Device, DeviceAdmin)
admin.site.register(DeviceOwner, DeviceOwnerAdmin)
admin.site.register(DeviceType, DeviceTypeAdmin)

admin.site.register(Material, MaterialAdmin)
admin.site.register(MaterialCategory, MaterialCategoryAdmin)
admin.site.register(TicketMaterial, TicketMaterialAdmin)
