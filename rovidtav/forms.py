# -*- coding: utf-8 -*-

from django.forms.models import ModelChoiceField
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django import forms

from .models import (Ticket, Note, Material, TicketMaterial, WorkItem,
                     TicketWorkItem, Payoff, Device, DeviceOwner)


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

    class Meta:
        model = TicketWorkItem
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
        device = super(DeviceForm, self).save(commit=commit)
        if owner:
            try:
                dev_owner = DeviceOwner.objects.get(device=device)
                ct = ContentType.objects.get(app_label='auth', model='user')
                dev_owner.content_type = ct
                dev_owner.object_id = owner.pk
                dev_owner.save()
            except DeviceOwner.DoesNotExist:
                DeviceOwner.objects.create(
                    device=device, content_type=owner.get_content_type_obj(),
                    object_id=owner.pk)
        return device


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
