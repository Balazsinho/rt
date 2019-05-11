# -*- coding: utf-8 -*-

import datetime

from django.forms.models import ModelChoiceField
from django.contrib.auth.models import User
from django.db.models import Q
from django import forms

from .models import (Ticket, Note, Material, TicketMaterial, WorkItem,
                     TicketWorkItem, Device, DeviceOwner, Const,
                     TicketType, NetworkTicketMaterial, NetworkTicketWorkItem,
                     Payoff)
from rovidtav.models import MaterialMovementMaterial, MaterialMovement,\
    DeviceReassignEvent, Warehouse, WarehouseLocation, DeviceType, NTNEWorkItem,\
    NTNEMaterial, NetworkTicket, BaseMaterial, MaterialWorkitemRule
from rovidtav.admin_helpers import ContentTypes, find_device_type
from django.core.exceptions import ValidationError


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


class MMAttachmentForm(AttachmentForm):

    class Meta:
        fields = ('materialmovement', '_data', 'remark')
        widgets = {
          'materialmovement': forms.HiddenInput(),
        }


class NTNEAttachmentForm(AttachmentForm):

    class Meta:
        fields = ('network_element', '_data', 'remark')
        widgets = {
          'network_element': forms.HiddenInput(),
        }


class IWIAttachmentForm(AttachmentForm):

    class Meta:
        fields = ('work_item', '_data', 'remark')
        widgets = {
          'work_item': forms.HiddenInput(),
        }


class NTAttachmentForm(forms.ModelForm):

    _data = forms.CharField(label=u'File', widget=forms.FileInput())
    name = forms.CharField(widget=forms.HiddenInput(), required=False)
    deviceupload = forms.CharField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        super(NTAttachmentForm, self).__init__(*args, **kwargs)
        if kwargs.get('initial', {}).get('deviceupload') is not None:
            self.fields['remark'].widget = forms.HiddenInput()

    class Meta:
        fields = ('ticket', '_data', 'remark')
        widgets = {
          'ticket': forms.HiddenInput(),
        }

    def clean__data(self):
        if '_data' in self.files:
            if self.data.get('deviceupload'):
                allowed_ext = ('.xls', '.xlsx')
                if not self.files['_data'].name.endswith(allowed_ext):
                    raise ValidationError(
                        u'Az eszköz felvitel fileok csak {} kiterjesztésűek '
                        u'lehetnek'.format(u', '.join(allowed_ext)))
            return self.files['_data'].read()

    def clean_name(self):
        if '_data' in self.files:
            return self.files['_data'].name

    def save(self, commit=True):
        if self.data.get('deviceupload'):
            return self.instance
        return super(NTAttachmentForm, self).save(commit=commit)

    def save_m2m(self):
        pass


class WarehouseForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(WarehouseForm, self).__init__(*args, **kwargs)
        if 'city' in self.fields:
            self.fields['city'].required = True

    class Meta:
        model = Warehouse
        widgets = {
          'owner': forms.HiddenInput(),
        }
        fields = '__all__'


class HandleOwner(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(HandleOwner, self).__init__(*args, **kwargs)
        owner_id = kwargs.get('initial', {}).get('owner')
        if 'owner' in self.fields and owner_id:
            owner = User.objects.get(id=owner_id)
            self.fields['owner'].initial = owner
            self.fields['owner'].widget = forms.HiddenInput()


class AddAutoWorkitem(object):

    # material to workitem model map
    MODEL_MAP = {
        TicketMaterial: TicketWorkItem,
        NetworkTicketMaterial: NetworkTicketWorkItem,
        NTNEMaterial: NTNEWorkItem,
    }

    def save(self, commit=True):
        result = super(AddAutoWorkitem, self).save(commit)
        material = self.cleaned_data['material']
        target = self.cleaned_data.get('ticket') or \
            self.cleaned_data.get('network_element')
        rules = MaterialWorkitemRule.objects.filter(material=material)
        material_model = self.Meta.model
        workitem_model = self.MODEL_MAP.get(material_model)
        if not workitem_model:
            return result
        for rule in rules:
            target_attr = 'ticket' if hasattr(workitem_model, 'ticket') \
                else 'network_element'
            work_item = rule.workitem
            amount = self.cleaned_data['amount'] \
                if rule.amount == MaterialWorkitemRule.ADD_EQUAL else 1
            owner = self.cleaned_data['owner']
            workitem_data = {
                'owner': owner,
                'work_item': work_item,
                'amount': amount,
                target_attr: target
            }
            workitem_model.objects.get_or_create(**workitem_data)
        return result


class TicketMaterialForm(HandleOwner):

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
            suggestions = Material.objects.filter(
                Q(technologies__contains=ticket.technology) |
                Q(technologies__contains=Const.MIND))
            self.fields['material'].queryset = suggestions

    class Meta:
        model = TicketMaterial
        widgets = {
          'ticket': forms.HiddenInput(),
        }
        fields = '__all__'


class MMMaterialForm(forms.ModelForm):

    material = ModelChoiceField(
        Material.objects.all(),
        widget=forms.Select(attrs={'style': 'width:500px', 'size': '10'}),
        label='Anyag',
    )

    class Meta:
        model = MaterialMovementMaterial
        widgets = {
          'materialmovement': forms.HiddenInput(),
        }
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(MMMaterialForm, self).__init__(*args, **kwargs)
        data = self.initial or self.data
        materialmovement = MaterialMovement.objects.get(
            id=int(data['materialmovement']))
        locations = materialmovement.target.warehouselocation_set.all()
        if locations:
            self.fields['location_to'].queryset = locations
        else:
            self.fields['location_to'].widget = forms.HiddenInput()
        pass


class TicketWorkItemForm(HandleOwner):

    work_item = ModelChoiceField(
        WorkItem.objects.all(),
        widget=forms.Select(attrs={'style': 'width:500px', 'size': '10'}),
        label='Munka',
    )

    def __init__(self, *args, **kwargs):
        super(TicketWorkItemForm, self).__init__(*args, **kwargs)
        ticket_id = kwargs.get('initial', {}).get('ticket')
        if ticket_id:
            ticket = Ticket.objects.get(pk=kwargs['initial']['ticket'])
            suggestions = WorkItem.objects.filter(
                Q(technologies__contains=ticket.technology) |
                Q(technologies__contains=Const.MIND))
            self.fields['work_item'].queryset = suggestions

    class Meta:
        model = TicketWorkItem
        widgets = {
          'ticket': forms.HiddenInput(),
        }
        fields = '__all__'


class NetworkTicketMaterialForm(AddAutoWorkitem, HandleOwner):

    material = ModelChoiceField(
        Material.objects.all(),
        widget=forms.Select(attrs={'style': 'width:500px', 'size': '10'}),
        label='Anyag',
    )

    def __init__(self, *args, **kwargs):
        super(NetworkTicketMaterialForm, self).__init__(*args, **kwargs)
        ticket_id = kwargs.get('initial', {}).get('ticket')
        suggestions_q = Q(technologies__contains=Const.HALOZAT)
        if ticket_id:
            ticket = NetworkTicket.objects.get(pk=kwargs['initial']['ticket'])
            for tech in ticket.technologies:
                suggestions_q |= Q(technologies__contains=tech)
        else:
            suggestions_q |= Q(technologies__contains=Const.MIND)
        suggestions = Material.objects.filter(suggestions_q)
        self.fields['material'].queryset = suggestions

    class Meta:
        model = NetworkTicketMaterial
        widgets = {
          'ticket': forms.HiddenInput(),
        }
        fields = '__all__'


class NTNEWorkItemForm(HandleOwner):

    class Meta:
        model = NTNEWorkItem
        widgets = {
          'network_element': forms.HiddenInput(),
        }
        fields = '__all__'


class NTNEMaterialForm(HandleOwner):

    class Meta:
        model = NTNEMaterial
        widgets = {
          'network_element': forms.HiddenInput(),
        }
        fields = '__all__'


class NetworkTicketWorkItemForm(HandleOwner):

    work_item = ModelChoiceField(
        WorkItem.objects.all(),
        widget=forms.Select(attrs={'style': 'width:500px', 'size': '10'}),
        label='Munka',
    )

    def __init__(self, *args, **kwargs):
        super(NetworkTicketWorkItemForm, self).__init__(*args, **kwargs)
        suggestions = WorkItem.objects.filter(
            Q(technologies__contains=Const.HALOZAT) |
            Q(technologies__contains=Const.MIND))
        self.fields['work_item'].queryset = suggestions

    class Meta:
        model = NetworkTicketWorkItem
        widgets = {
          'ticket': forms.HiddenInput(),
        }
        fields = '__all__'


class NoteForm(forms.ModelForm):

    fields = ('content_type', 'object_id', 'content_object',
              'is_history', 'remark')

    class Meta:
        model = Note
        widgets = {
          'object_id': forms.HiddenInput(),
          'content_type': forms.HiddenInput(),
          'is_history': forms.HiddenInput(),
        }
        fields = '__all__'


class DeviceOwnerForm(forms.ModelForm):

    sn = forms.CharField(label=u'Szériaszám', required=False)
    ticket_id = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = DeviceOwner
        fields = '__all__'
        widgets = {
            'object_id': forms.HiddenInput(),
            'content_type': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super(DeviceOwnerForm, self).__init__(*args, **kwargs)
        self.fields['device'].required = False
        ticket = None

        data = self.initial or self.data
        if data['content_type'] == str(ContentTypes.client.id):
            try:
                ticket = Ticket.objects.get(id=data['ticket_id'])
            except KeyError, Ticket.DoesNotExist:
                pass

        if ticket and ticket.owner:
            warehouse = Warehouse.objects.get(owner=ticket.owner)
            allowed_pks = DeviceOwner.objects.filter(
                content_type=ContentTypes.warehouse, object_id=warehouse.id).values_list('device__id', flat=True)
            self.fields['device'].queryset = Device.objects.filter(id__in=allowed_pks, returned_at__isnull=True)
        else:
            self.fields['device'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super(DeviceOwnerForm, self).clean()
        if not cleaned_data['sn'] and not cleaned_data['device']:
            raise forms.ValidationError(u'Nem maradhat minden mező üresen')
        return cleaned_data

    def save(self, commit=True):
        if self.cleaned_data['device']:
            device = self.cleaned_data['device']
        else:
            device, _ = Device.objects.get_or_create(sn=self.cleaned_data['sn'])
        if not device.type:
            find_device_type(device)
        try:
            self.instance = DeviceOwner.objects.get(device=device)
        except DeviceOwner.DoesNotExist:
            self.instance.device = device

        self.instance.content_type = self.cleaned_data['content_type']
        self.instance.object_id = self.cleaned_data['object_id']
        return super(DeviceOwnerForm, self).save(commit=commit)


class DeviceReassignEventForm(forms.ModelForm):

    sn = forms.CharField(
        label=u'Szériaszám',
        widget=forms.Textarea(),
        help_text=u'Írj be egy szériaszámot vagy csipogj be bármennyit')
    type = ModelChoiceField(
        required=False, queryset=DeviceType.objects.all(),
        label=u'Típus',
        help_text=u'Csak akkor kell megadni ha nem akarjuk az automatikus '
        u'felismerést használni')

    class Meta:
        model = DeviceReassignEvent
        fields = '__all__'
        widgets = {
            'device': forms.HiddenInput(),
            'materialmovement': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super(DeviceReassignEventForm, self).__init__(*args, **kwargs)
        self.fields['device'].required = False

    def clean_sn(self):
        if not self.cleaned_data['sn'].strip():
            raise ValidationError(u'A mezőben nincs használható adat')
        return self.cleaned_data['sn']

    def save(self, commit=True):
        mm = self.cleaned_data['materialmovement']
        dev_type = self.cleaned_data['type']
        for sn in self.cleaned_data['sn'].split():
            sn = sn.strip()
            if not sn:
                continue
            device, _ = Device.objects.get_or_create(sn=sn)
            if not dev_type:
                find_device_type(device)
            else:
                device.type = dev_type
                device.save()
            if not self.instance.device_id:
                self.instance.device = device
                continue
            DeviceReassignEvent.objects.get_or_create(materialmovement=mm,
                                                      device=device)
        return super(DeviceReassignEventForm, self).save(commit=commit)

    def save_m2m(self):
        pass


class DeviceToCustomerForm(forms.Form):

    owner = ModelChoiceField(queryset=User.objects.all(),
                             label=u'Tulajdonos')


class MaterialMovementForm(forms.ModelForm):

    devices_num = forms.CharField(label=u'Eszközök száma', required=False)

    def __init__(self, *args, **kwargs):
        super(MaterialMovementForm, self).__init__(*args, **kwargs)
        self.fields['devices_num'].disabled = True
        self.fields['source'].required = True
        self.fields['target'].required = True
        if self.instance and self.instance.id:
            devices = self.instance.devicereassignevent_set.all().count()
            self.initial['devices_num'] = devices
        else:
            self.fields['devices_num'].widget = forms.HiddenInput()

    class Meta:
        model = MaterialMovement
        fields = ('source', 'target', 'delivery_num', 'created_at')
        widgets = {
            'finalized': forms.HiddenInput(),
            'ticket_tags': forms.HiddenInput(),
        }


class TicketForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(TicketForm, self).__init__(*args, **kwargs)
        if 'payoffs' in self.fields:
            suggestions = Payoff.objects.all().order_by('-year', '-month', '-name')
            self.fields['payoffs'].queryset = suggestions

    class Media:
        js = ('js/ticket_form.js',)


class PayoffForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(PayoffForm, self).__init__(*args, **kwargs)
        now = datetime.datetime.now()
        self.fields['year'].choices = [(i, i) for i in
                                       range(now.year-1, now.year+2)]
        self.fields['year'].initial = now.year
        self.fields['month'].initial = now.month


class TicketTypeForm(forms.ModelForm):

    class Meta:
        model = TicketType
        fields = '__all__'
        widgets = {
            'network_ticket': forms.HiddenInput(),
        }


class WorkItemForm(forms.ModelForm):

    technologies = forms.MultipleChoiceField(choices=Const.get_tech_choices(),
                                             required=False,
                                             label=u'Technológia')


class MaterialForm(forms.ModelForm):

    technologies = forms.MultipleChoiceField(choices=Const.get_tech_choices(),
                                             required=False,
                                             label=u'Technológia')
    integrate_here = forms.ModelChoiceField(
        queryset=Material.objects.all(), required=False,
        label=u'Anyag egyesítése ide',
        help_text=u'Az itt kiválasztott anyag minden előfordulása átíródik az '
        u'éppen szerkesztett anyagra, a kiválasztott anyag törlődik')

    def save(self, commit=True):
        if self.cleaned_data['integrate_here']:
            integrate_here = self.cleaned_data['integrate_here']
            for cls in BaseMaterial.__subclasses__():
                cls.objects.filter(material=integrate_here) \
                    .update(material=self.instance)
            integrate_here.delete()
        return super(MaterialForm, self).save(commit)


class WarehouseLocationForm(forms.ModelForm):

    class Meta:
        model = WarehouseLocation
        fields = '__all__'
        widgets = {
            'warehouse': forms.HiddenInput(),
        }


class NetworkTicketForm(forms.ModelForm):

    technologies = forms.MultipleChoiceField(choices=Const.get_tech_choices(),
                                             required=False,
                                             label=u'Technológia')
