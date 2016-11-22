# -*- coding: utf-8 -*-

from django import forms
from django.db.models import Q
from django.db.models.fields import DateTimeField, DateField
from django.db.models.fields.related import ForeignObjectRel

from django.forms.fields import DateField, ChoiceField

from model_report.widgets import RangeField
from model_report.report import ReportAdmin
from django.core.exceptions import FieldDoesNotExist


class FilterForm(forms.BaseForm):

    def __init__(self, *args, **kwargs):
        self.base_fields = args[0]
        super(FilterForm, self).__init__(**kwargs)
        self.filter_report_is_all = tuple(self.fields) == ('__all__',)
        for name, field in self.fields.items():
            if hasattr(field, 'queryset'):
                qs = field.queryset
                if name in qs.model._meta.get_fields():
                    field.queryset = qs.filter(Q(**{name: field}))

        for field in self.fields:
            self.fields[field].required = False

    def _post_clean(self):
        pass

    def get_filter_kwargs(self):
        if not self.is_valid():
            return {}
        filter_kwargs = dict(self.cleaned_data)
        return filter_kwargs
        for k, v in self.cleaned_data.items():
            if not v:
                filter_kwargs.pop(k)
                continue
            if k == '__all__': 
                filter_kwargs.pop(k)
                continue
            if isinstance(v, (list, tuple)):
                if isinstance(self.fields[k], (RangeField)):
                    filter_kwargs.pop(k)
                    start_range, end_range = v
                    if start_range:
                        filter_kwargs['%s__gte' % k] = start_range
                    if end_range:
                        filter_kwargs['%s__lte' % k] = end_range
            elif hasattr(self.fields[k], 'as_boolean'):
                if v:
                    filter_kwargs.pop(k)
                    filter_kwargs[k] = (unicode(v) == u'True')
        return filter_kwargs

    def get_cleaned_data(self):
        return getattr(self, 'cleaned_data', {})


class CustomReportAdmin(ReportAdmin):

    # Classes for the list filters if not using the original one
    list_filter_classes = {}

    # To filter on attributes, not just fields
    attr_filters = {}

    def _choicefield(self, model_field_name, base_model):
        choices = set([getattr(o, model_field_name)
                       for o in base_model.objects.all()
                       if getattr(o, model_field_name)])
        choices = sorted([(c, c) for c in choices])
        choices.insert(0, ('', '-------'))
        return ChoiceField(choices, required=False)

    def _datefield(self, model_field_name, base_model):
        return DateField

    def _is_relation(self, field):
        return isinstance(field, ForeignObjectRel)

    def get_form_filter(self, request):
        if not self.list_filter:
            form_fields = {
                '__all__': forms.BooleanField(label='',
                                              widget=forms.HiddenInput,
                                              initial='1')
            }
        else:
            form_fields = {}
            for field_name in self.list_filter:
                model_names = field_name.split('__')
                model_field_name = model_names.pop(-1)
                base_model = self.model
                for e in model_names:
                    base_model = base_model._meta.get_field(e).rel.to

                model_field = base_model._meta.get_field(model_field_name)

                if isinstance(model_field, (DateField, DateTimeField)):
                    field = RangeField(model_field.formfield)

                elif not hasattr(model_field, 'formfield'):
                    field = forms.ModelChoiceField(queryset=model_field.model.objects.all())

                else:
                    field = model_field.formfield()

                if field_name in self.list_filter_classes:
                    self.list_filter_classes[field_name]

                field.label = self.override_field_labels.get(field_name) or model_field_name

                # Provide a hook for updating the queryset
                if hasattr(field, 'queryset') and field_name in self.override_field_choices:
                    field.queryset = self.override_field_choices.get(field_name)(self, field.queryset)
                form_fields[field_name] = field

        form = FilterForm(form_fields, data=request.GET or None)
        form.is_valid()

        return form

    def get_column_names(self, ignore_columns={}):
        """
        Return the list of columns
        """
        values = []
        for field, field_name in self.model_fields:
            if field_name in ignore_columns:
                continue
            caption = self.override_field_labels.get(field_name, field.verbose_name)
            values.append(caption)
        return values
