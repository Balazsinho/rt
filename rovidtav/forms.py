# -*- coding: utf-8 -*-

import datetime

from django.forms.models import ModelChoiceField
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django import forms

from .models import (Ticket, Note, Material, TicketMaterial, WorkItem,
                     TicketWorkItem, Device, DeviceOwner, Const,
                     TicketType, NetworkTicketMaterial, NetworkTicketWorkItem,
                     Payoff)
from rovidtav.models import MaterialMovementMaterial


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

    def __init__(self, *args, **kwargs):
        super(MMMaterialForm, self).__init__(*args, **kwargs)

    class Meta:
        model = MaterialMovementMaterial
        widgets = {
          'materialmovement': forms.HiddenInput(),
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


class NetworkTicketMaterialForm(forms.ModelForm):

    material = ModelChoiceField(
        Material.objects.all(),
        widget=forms.Select(attrs={'style': 'width:500px', 'size': '10'}),
        label='Anyag',
    )

    def __init__(self, *args, **kwargs):
        super(NetworkTicketMaterialForm, self).__init__(*args, **kwargs)
        suggestions = Material.objects.filter(
            Q(technologies__contains=Const.HALOZAT) |
            Q(technologies__contains=Const.MIND))
        self.fields['material'].queryset = suggestions

    class Meta:
        model = NetworkTicketMaterial
        widgets = {
          'ticket': forms.HiddenInput(),
        }
        fields = '__all__'


class NetworkTicketWorkItemForm(forms.ModelForm):

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


class DeviceForm(forms.ModelForm):

    owner = ModelChoiceField(queryset=User.objects.all(),
                             label=u'Tulajdonos')

    class Meta:
        model = Device
        fields = '__all__'

    def save(self, commit=True):
        owner = self.cleaned_data.get('owner', None)
        device = super(DeviceForm, self).save(commit=True)
        if owner:
            user_ct = ContentType.objects.get(app_label='auth', model='user')
            try:
                dev_owner = DeviceOwner.objects.get(device=device)
                dev_owner.content_type = user_ct
                dev_owner.object_id = owner.pk
                dev_owner.save()
            except DeviceOwner.DoesNotExist:
                DeviceOwner.objects.create(
                    device=device, content_type=user_ct,
                    object_id=owner.pk)
        return device

    def save_m2m(self, commit=True):
        pass


class DeviceOwnerForm(forms.ModelForm):

    class Meta:
        model = DeviceOwner
        fields = '__all__'
        widgets = {
            'object_id': forms.HiddenInput(),
            'content_type': forms.HiddenInput(),
        }

    def save(self, commit=True):
        try:
            self.instance = DeviceOwner.objects.get(device=self.instance.device)
            self.instance.content_type = self.cleaned_data.get('content_type', None)
            self.instance.object_id = self.cleaned_data.get('object_id', None)
        except DeviceOwner.DoesNotExist:
            pass
        return super(DeviceOwnerForm, self).save(commit=commit)


class DeviceToCustomerForm(forms.Form):

    owner = ModelChoiceField(queryset=User.objects.all(),
                             label=u'Tulajdonos')


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
