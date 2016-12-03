# -*- coding: utf-8 -*-

from xlwt import Workbook, easyxf

from django import forms
from django.db.models import Q
from django.db.models.fields import DateTimeField, DateField
from django.db.models.fields.related import ForeignObjectRel
from django.http.response import HttpResponse
from django.forms.fields import ChoiceField

from model_report.widgets import RangeField
from model_report.report import ReportAdmin, FitSheetWrapper
from model_report.export_pdf import render_to_pdf


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

    def _insert_extra_columns(self, column_names, qs):
        pass

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

    def get_query_set(self, filter_kwargs):
        """
        Return the the queryset
        """
        qs = self.model.objects.all()
        for q_key, q_value in filter_kwargs.items():
            if q_value:
                if hasattr(q_value, 'values_list'):
                    q_value = q_value.values_list('pk', flat=True)
                    q_key = '%s__pk__in' % q_key.split("__")[0]
                elif isinstance(q_value, list):
                    q_key = '%s__range' % q_key
                qs = qs.filter(Q(**{q_key: q_value}))
        query_set = qs.distinct()
        return query_set

    def get_render_context(self, request, extra_context={}, by_row=None):
        context_request = request or self.request
        related_fields = []
        filter_related_fields = {}
        if self.parent_report and by_row:
            for mfield, cfield, index in self.related_inline_filters:
                filter_related_fields[cfield] = by_row[index].value

        try:
            form_groupby = self.get_form_groupby(context_request)
            form_filter = self.get_form_filter(context_request)
            form_config = self.get_form_config(context_request)

            qs = self.get_query_set(filter_related_fields or form_filter.get_filter_kwargs())

            column_labels = self.get_column_names(qs, filter_related_fields)
            report_rows = []
            groupby_data = None
            filter_kwargs = None
            report_anchors = []
            chart = None

            context = {
                'report': self,
                'form_groupby': form_groupby,
                'form_filter': form_filter,
                'form_config': form_config if self.type == 'chart' else None,
                'chart': chart,
                'report_anchors': report_anchors,
                'column_labels': column_labels,
                'report_rows': report_rows,
            }

            if context_request.GET:
                groupby_data = form_groupby.get_cleaned_data() if form_groupby else None
                filter_kwargs = filter_related_fields or form_filter.get_filter_kwargs()
                if groupby_data:
                    self.__dict__.update(groupby_data)
                else:
                    self.__dict__['onlytotals'] = False
                report_rows = self.get_rows(context_request, groupby_data, filter_kwargs, filter_related_fields)

                for g, r in report_rows:
                    report_anchors.append(g)

                if len(report_anchors) <= 1:
                    report_anchors = []

                if self.type == 'chart' and groupby_data and groupby_data['groupby']:
                    config = form_config.get_config_data()
                    if config:
                        chart = self.get_chart(config, report_rows)

                if self.onlytotals:
                    for g, rows in report_rows:
                        for r in list(rows):
                            if r.is_value():
                                rows.remove(r)

                if not context_request.GET.get('export', None) is None and not self.parent_report:
                    if context_request.GET.get('export') == 'excel':
                        book = Workbook(encoding='utf-8')
                        sheet1 = FitSheetWrapper(book.add_sheet(self.get_title()[:20]))
                        stylebold = easyxf('font: bold true; alignment:')
                        stylevalue = easyxf('alignment: horizontal left, vertical top;')
                        row_index = 0
                        for index, x in enumerate(column_labels):
                            sheet1.write(row_index, index, u'%s' % x, stylebold)
                        row_index += 1

                        for g, rows in report_rows:
                            if g:
                                sheet1.write(row_index, 0, u'%s' % x, stylebold)
                                row_index += 1
                            for row in list(rows):
                                if row.is_value():
                                    for index, x in enumerate(row):
                                        if isinstance(x.value, (list, tuple)):
                                            xvalue = ''.join(['%s\n' % v for v in x.value])
                                        else:
                                            xvalue = x.text()
                                        sheet1.write(row_index, index, xvalue, stylevalue)
                                    row_index += 1
                                elif row.is_caption:
                                    for index, x in enumerate(row):
                                        if not isinstance(x, (unicode, str)):
                                            sheet1.write(row_index, index, x.text(), stylebold)
                                        else:
                                            sheet1.write(row_index, index, x, stylebold)
                                    row_index += 1
                                elif row.is_total:
                                    for index, x in enumerate(row):
                                        sheet1.write(row_index, index, x.text(), stylebold)
                                        sheet1.write(row_index + 1, index, ' ')
                                    row_index += 2

                        response = HttpResponse(content_type="application/ms-excel")
                        response['Content-Disposition'] = 'attachment; filename=%s.xls' % self.slug
                        book.save(response)
                        return response
                    if context_request.GET.get('export') == 'pdf':
                        inlines = [ir(self, context_request) for ir in self.inlines]
                        report_anchors = None
                        setattr(self, 'is_export', True)
                        context = {
                            'report': self,
                            'column_labels': column_labels,
                            'report_rows': report_rows,
                            'report_inlines': inlines,
                        }
                        context.update({'pagesize': 'legal landscape'})
                        return render_to_pdf(self, 'model_report/export_pdf.html', context)

            inlines = [ir(self, context_request) for ir in self.inlines]

            is_inline = self.parent_report is None
            render_report = not (len(report_rows) == 0 and is_inline)
            context = {
                'render_report': render_report,
                'is_inline': is_inline,
                'inline_column_span': 0 if is_inline else len(self.parent_report.get_column_names(qs)),
                'report': self,
                'form_groupby': form_groupby,
                'form_filter': form_filter,
                'form_config': form_config if self.type == 'chart' else None,
                'chart': chart,
                'report_anchors': report_anchors,
                'column_labels': column_labels,
                'report_rows': report_rows,
                'report_inlines': inlines,
            }

            if extra_context:
                context.update(extra_context)

            context['request'] = request
            return context
        finally:
            globals()['_cache_class'] = {}
