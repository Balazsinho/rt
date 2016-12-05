# -*- coding: utf-8 -*-
from collections import OrderedDict

from django import forms
from django.db.models import Q
from django.db.models.query import QuerySet
from django.db.models.fields import DateTimeField, DateField
from django.forms.fields import ChoiceField

from model_report.widgets import RangeField
from model_report.report import ReportAdmin

from rovidtav.admin_helpers import is_site_admin


class Label(object):

    def __init__(self, label):
        self.label = label

    def __call__(self, _, field):
        return self.label


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


class CustomQuerySet(QuerySet):

    extra_col_map = {}
    extra_cols = []

    def values_list(self, *fields, **kwargs):
        fields = list(fields)
        fields.insert(0, 'pk')
        fields = [f for f in fields if f not in [c[1] for c in self.extra_cols]]
        clone = super(CustomQuerySet, self).values_list(*fields, **kwargs)
        values_list = list(clone)
        final_list = []
        for row in values_list:
            row = list(row)
            pk = row.pop(0)
            extra_values = self.extra_col_map.get(pk, {})
            for col_idx, col in self.extra_cols:
                val = extra_values.get(col)
                row.insert(col_idx, val)
            final_list.append(row)
        return final_list

    def _clone(self, **kwargs):
        clone = super(CustomQuerySet, self)._clone(**kwargs)
        clone.extra_col_map = self.extra_col_map
        clone.extra_cols = self.extra_cols
        return clone


class CustomReportAdmin(ReportAdmin):

    extra_columns_first_col = 0
    # This one is set only if the logged in user is not an admin
    data_owner = None
    data_owner_field = 'owner'

    def _calc_extra_from_qs(self, qs):
        pass

    def _calculate_extra_columns(self, request, by_row):
        self._check_admin_user(request)
        context_request = request or self.request
        filter_related_fields = {}
        if self.parent_report and by_row:
            for _, cfield, index in self.related_inline_filters:
                filter_related_fields[cfield] = by_row[index].value
        form_filter = self.get_form_filter(context_request)
        qs = self.get_query_set(filter_related_fields or form_filter.get_filter_kwargs())
        self._calc_extra_from_qs(qs)

    def get_form_filter(self, request):
        self._check_admin_user(request)
        if not self.list_filter:
            form_fields = {
                '__all__': forms.BooleanField(label='',
                                              widget=forms.HiddenInput,
                                              initial='1')
            }
        else:
            form_fields = OrderedDict()
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
                    field_cls = self.list_filter_classes[field_name]
                    if field_cls == ChoiceField:
                        all_choices = [getattr(inst, model_field_name) for inst in base_model.objects.all()]
                        all_choices = filter(lambda x: x is not None, all_choices)
                        choices = [(item, item) for item in sorted(list(set(all_choices)))]
                        choices.insert(0, ('', '---------'))
                        field = field_cls(choices)

                override_field_name = self.override_field_labels.get(field_name)
                field.label = override_field_name(None, None) if override_field_name else model_field.verbose_name

                # Provide a hook for updating the queryset
                if hasattr(field, 'queryset') and field_name in self.override_field_choices:
                    field.queryset = self.override_field_choices.get(field_name)(self, field.queryset)
                form_fields[field_name] = field

        form = FilterForm(form_fields, data=request.GET or None)
        form.is_valid()

        return form

    def get_column_names(self, ignore_columns={}):
        names = super(CustomReportAdmin, self).get_column_names(ignore_columns)
        for extra_idx, extra_name in self.calculated_columns:
            names.insert(extra_idx, extra_name)
        return names

    def get_query_field_names(self):
        values = []
        for field in self.get_fields():
            if 'self.' not in field:
                values.append(field.split(".")[0])
            else:
                values.append(field)
        if hasattr(self, 'calculated_columns'):
            for col_idx, col in self.calculated_columns:
                values.insert(col_idx, col)
        return values

    def get_query_set(self, filter_kwargs):
        """
        Return the the queryset
        """
        qs = self.model.objects.all()
        if self.data_owner:
            filter_kwargs[self.data_owner_field] = self.data_owner.pk
        for q_key, q_value in filter_kwargs.items():
            if q_value:
                if hasattr(q_value, 'values_list'):
                    q_value = q_value.values_list('pk', flat=True)
                    q_key = '%s__pk__in' % q_key.split("__")[0]
                elif isinstance(q_value, list):
                    q_key = '%s__range' % q_key
                qs = qs.filter(Q(**{q_key: q_value}))
        self._calc_extra_from_qs(qs)
        qs.__class__ = CustomQuerySet
        qs.extra_col_map = self.extra_col_map
        qs.extra_cols = self.calculated_columns
        query_set = qs.distinct()
        return query_set

    def _check_admin_user(self, request):
        if not self.data_owner and not is_site_admin(request.user):
            self.data_owner = request.user

    def get_render_context(self, request, extra_context={}, by_row=None):
        self._check_admin_user(request)
        self._calculate_extra_columns(request, by_row)
        return super(CustomReportAdmin, self).get_render_context(
            request, extra_context, by_row)
