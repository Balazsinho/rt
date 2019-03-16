# -*- coding: utf-8 -*-
from collections import OrderedDict
import re

from xlwt import Workbook, easyxf
from django import forms
from django.db.models import Q
from django.db.models.query import QuerySet
from django.db.models.fields import DateTimeField, DateField
from django.forms.fields import ChoiceField
from django.http.response import HttpResponse

from model_report.export_pdf import render_to_pdf
from model_report.widgets import RangeField
from model_report.report import ReportAdmin, FitSheetWrapper

from rovidtav.admin_helpers import is_site_admin
from model_report import arial10


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


class FitSheetWrapper(object):
    """Try to fit columns to max size of any entry.
    To use, wrap this around a worksheet returned from the
    workbook's add_sheet method, like follows:

        sheet = FitSheetWrapper(book.add_sheet(sheet_name))

    The worksheet interface remains the same: this is a drop-in wrapper
    for auto-sizing columns.
    """
    def __init__(self, sheet):
        self.sheet = sheet
        self.widths = dict()
        self.heights = dict()

    def write(self, r, c, label='', *args, **kwargs):
        self.sheet.write(r, c, label, *args, **kwargs)
        self.sheet.row(r).collapse = True
        bold = False
        if args:
            style = args[0]
            bold = str(style.font.bold) in ('1', 'true', 'True')
        try:
            width = int(arial10.fitwidth(label, bold))
            if width > self.widths.get(c, 0):
                self.widths[c] = width
                self.sheet.col(c).width = width

            height = int(arial10.fitheight(label, bold))
            if height > self.heights.get(r, 0):
                self.heights[r] = height
                self.sheet.row(r).height = height
        except:
            pass

    def __getattr__(self, attr):
        return getattr(self.sheet, attr)


class CustomReportAdmin(ReportAdmin):

    extra_columns_first_col = 0
    calculated_columns = []
    list_filter_classes = {}
    id_url_map = {}
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
        if not form_filter.get_filter_kwargs():
            return
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
        return self._get_render_context(request, extra_context,
                                        by_row)
#        return super(CustomReportAdmin, self).get_render_context(
#            request, extra_context, by_row)

    def _get_render_context(self, request, extra_context={}, by_row=None):
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

            column_labels = self.get_column_names(filter_related_fields)
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
                                        if re.match('^\d+$', xvalue):
                                            sheet1.write(row_index, index, int(xvalue))
                                        else:
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
                'inline_column_span': 0 if is_inline else len(self.parent_report.get_column_names()),
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


class DedupedReportRows(CustomReportAdmin):

    def get_rows(self, request, groupby_data=None, filter_kwargs={}, filter_related_fields={}):
        # We deduplicate the rows
        rows = CustomReportAdmin.get_rows(self, request, groupby_data=groupby_data, filter_kwargs=filter_kwargs, filter_related_fields=filter_related_fields)
        dedup_rows = []
        for row in rows[0][1]:
            row_val = [col.value for col in row]
            append = True
            for dedup_row in dedup_rows:
                dedup_row_val = [col.value for col in dedup_row]
                if row_val == dedup_row_val:
                    append = False
                    break
            if append:
                dedup_rows.append(row)
        rows[0][1] = dedup_rows
        return rows
