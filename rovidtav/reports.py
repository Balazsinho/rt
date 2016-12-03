# -*- coding: utf-8 -*-
from itertools import groupby

from django.forms.fields import ChoiceField
from django.conf import settings
from django.utils.encoding import force_unicode

from model_report.report import reports
from model_report.utils import ReportValue, ReportRow

from rovidtav.report_helpers import CustomReportAdmin
from rovidtav.models import Ticket


class SummaryList(CustomReportAdmin):
    title = u'Összesítő lista'
    model = Ticket
    fields = [
        'ext_id',
        'city__name',
        'address',
        'city__primer',
        'owner',
        'closed_at',
    ]

    list_filter = ('city__primer', 'owner', 'closed_at')
    list_filter_classes = {
        'city__primer': ChoiceField,
    }
    list_order_by = ('ext_id',)
    type = 'report'
    override_field_labels = {
        'owner': u'Tulajdonos',
        'closed_at': u'Lezárva',
    }

    extra_columns_first_col = 4

#    def get_fields(self):
#        return CustomReportAdmin.get_fields(self) + ['a']

    def get_extra_columns(self, queryset):
        material_keys = []
        for ticket in queryset:
            f = ticket.anyag_jegy.all()
            material_keys.extend([m.material.sn for m in ticket.anyag_jegy.all()])
        material_keys = sorted(list(set(material_keys)))
        wo_offsets = list(enumerate(material_keys))
        return [(e[0]+self.extra_columns_first_col, e[1]) for e in wo_offsets]

    def get_column_names(self, qs=[], ignore_columns={}):
        names = super(SummaryList, self).get_column_names(ignore_columns)
        for extra_idx, extra_name in self.get_extra_columns(qs):
            names.insert(extra_idx, extra_name)
        return names

    def get_rows(self, request, groupby_data=None, filter_kwargs={}, filter_related_fields={}):
        report_rows = []

        def get_field_value(obj, field):
            if isinstance(obj, (dict)):
                return obj[field]
            left_field = field.split("__")[0]
            try:
                right_field = "__".join(field.split("__")[1:])
            except:
                right_field = ''
            if right_field:
                return get_field_value(getattr(obj, left_field), right_field)
            if hasattr(obj, 'get_%s_display' % left_field):
                attr = getattr(obj, 'get_%s_display' % field)
            else:
                attr = getattr(obj, field)
            if callable(attr):
                attr = attr()
            return attr

        for kwarg, value in filter_kwargs.items():
            if kwarg in self.override_field_filter_values:
                filter_kwargs[kwarg] = self.override_field_filter_values.get(kwarg)(self, value)

        qs = self.get_query_set(filter_kwargs)
        ffields = [f if 'self.' not in f else 'pk' for f in self.get_query_field_names() if f not in filter_related_fields]
        extra_ffield = []
        backend = settings.DATABASES['default']['ENGINE'].split('.')[-1]
        for f in list(ffields):
            if '__' in f:
                for field, name in self.model_fields:
                    if name == f:
                        if 'fields.Date' in unicode(field):
                            fname, flookup = f.rsplit('__', 1)
                            fname = fname.split('__')[-1]
                            if not flookup in ('year', 'month', 'day'):
                                break
                            if flookup == 'year':
                                if 'sqlite' in backend:
                                    extra_ffield.append([f, "strftime('%%Y', " + fname + ")"])
                                elif 'postgres' in backend:
                                    extra_ffield.append([f, "cast(extract(year from " + fname + ") as integer)"])
                                elif 'mysql' in backend:
                                    extra_ffield.append([f, "YEAR(" + fname + ")"])
                                else:
                                    raise NotImplemented  # mysql
                            if flookup == 'month':
                                if 'sqlite' in backend:
                                    extra_ffield.append([f, "strftime('%%m', " + fname + ")"])
                                elif 'postgres' in backend:
                                    extra_ffield.append([f, "cast(extract(month from " + fname + ") as integer)"])
                                elif 'mysql' in backend:
                                    extra_ffield.append([f, "MONTH(" + fname + ")"])
                                else:
                                    raise NotImplemented  # mysql
                            if flookup == 'day':
                                if 'sqlite' in backend:
                                    extra_ffield.append([f, "strftime('%%d', " + fname + ")"])
                                elif 'postgres' in backend:
                                    extra_ffield.append([f, "cast(extract(day from " + fname + ") as integer)"])
                                elif 'mysql' in backend:
                                    extra_ffield.append([f, "DAY(" + fname + ")"])
                                else:
                                    raise NotImplemented  # mysql
                        break
        obfields = list(self.list_order_by)
        if groupby_data and groupby_data['groupby']:
            if groupby_data['groupby'] in obfields:
                obfields.remove(groupby_data['groupby'])
            obfields.insert(0, groupby_data['groupby'])
        qs = self.filter_query(qs)
        qs = qs.order_by(*obfields)
        if extra_ffield:
            qs = qs.extra(select=dict(extra_ffield))

        material_keys = set()
        id_material_map = {}
        for ticket in qs:
            tms = ticket.anyag_jegy.all()
            material_keys |= set([tm.material for tm in tms])
            id_material_map[ticket.pk] = dict([(tm.material.sn, tm.amount) for tm in tms])

        extra_cols = self.get_extra_columns(qs)
        qs_list = []

        for rec in qs:
            list_item = []
            for field in ffields:
                field_value = rec
                for field_element in field.split('__'):
                    field_value = getattr(field_value, field_element)
                list_item.append(field_value)

            for extra_idx, extra_attr_name in extra_cols:
                attr_value = id_material_map.get(rec.pk, {}).get(extra_attr_name)
                list_item.insert(extra_idx, attr_value)

            qs_list.append(list_item)

        for extra_idx, extra_attr_name in extra_cols:
            ffields.insert(extra_idx, extra_attr_name)

        def get_with_dotvalues(resources):
            # {1: 'field.method'}
            dot_indexes = dict([(index, dot_field) for index, dot_field in enumerate(self.get_fields()) if '.' in dot_field])
            dot_indexes_values = {}

            dot_model_fields = [(index, model_field[0]) for index, model_field in enumerate(self.model_fields) if index in dot_indexes]
            # [ 1, model_field] ]
            for index, model_field in dot_model_fields:
                model_ids = set([row[index] for row in resources])
                if isinstance(model_field, (unicode, str)) and 'self.' in model_field:
                    model_qs = self.model.objects.filter(pk__in=model_ids)
                else:
                    model_qs = model_field.rel.to.objects.filter(pk__in=model_ids)
                div = {}
                method_name = dot_indexes[index].split('.')[1]
                for obj in model_qs:
                    method_value = getattr(obj, method_name)
                    if callable(method_value):
                        method_value = method_value()
                    div[obj.pk] = method_value
                dot_indexes_values[index] = div
                del model_qs

            if dot_indexes_values:
                new_resources = []
                for index_row, old_row in enumerate(resources):
                    new_row = []
                    for index, actual_value in enumerate(old_row):
                        if index in dot_indexes_values:
                            new_value = dot_indexes_values[index][actual_value]
                        else:
                            new_value = actual_value
                        new_row.append(new_value)
                    new_resources.append(new_row)
                resources = new_resources
            return resources

        def compute_row_totals(row_config, row_values, is_group_total=False, is_report_total=False):
            total_row = self.get_empty_row_asdict(self.get_fields(), ReportValue(' '))
            for k, v in total_row.items():
                if k in row_config:
                    fun = row_config[k]
                    value = fun(row_values[k])
                    if k in self.get_m2m_field_names():
                        value = ReportValue([value, ])
                    value = ReportValue(value)
                    value.is_value = False
                    value.is_group_total = is_group_total
                    value.is_report_total = is_report_total
                    if k in self.override_field_values:
                        value.to_value = self.override_field_values[k]
                    if k in self.override_field_formats:
                        value.format = self.override_field_formats[k]
                    value.is_m2m_value = (k in self.get_m2m_field_names())
                    total_row[k] = value
            row = self.reorder_dictrow(total_row)
            row = ReportRow(row)
            row.is_total = True
            return row

        def compute_row_header(row_config):
            header_row = self.get_empty_row_asdict(self.get_fields(), ReportValue(''))
            for k, fun in row_config.items():
                if hasattr(fun, 'caption'):
                    value = force_unicode(fun.caption)
                else:
                    value = '&nbsp;'
                header_row[k] = value
            row = self.reorder_dictrow(header_row)
            row = ReportRow(row)
            row.is_caption = True
            return row

        def group_m2m_field_values(gqs_values):
            values_results = []
            m2m_indexes = [index for ffield, lkfield, index, field in self.model_m2m_fields]

            def get_key_values(gqs_vals):
                return [v if index not in m2m_indexes else None for index, v in enumerate(gqs_vals)]

            # gqs_values needs to already be sorted on the same key function
            # for groupby to work properly
            gqs_values.sort(key=get_key_values)
            res = groupby(gqs_values, key=get_key_values)
            row_values = {}
            for key, values in res:
                row_values = dict([(index, []) for index in m2m_indexes])
                for v in values:
                    for index in m2m_indexes:
                        if v[index] not in row_values[index]:
                            row_values[index].append(v[index])
                for index, vals in row_values.items():
                    key[index] = vals
                values_results.append(key)
            return values_results

        qs_list = get_with_dotvalues(qs_list)
        if self.model_m2m_fields:
            qs_list = group_m2m_field_values(qs_list)

        groupby_fn = None
        if groupby_data and groupby_data['groupby']:
            groupby_field = groupby_data['groupby']
            if groupby_field in self.override_group_value:
                transform_fn = self.override_group_value.get(groupby_field)
                groupby_fn = lambda x: transform_fn(x[ffields.index(groupby_field)])
            else:
                groupby_fn = lambda x: x[ffields.index(groupby_field)]
        else:
            groupby_fn = lambda x: None

        qs_list.sort(key=groupby_fn)
        g = groupby(qs_list, key=groupby_fn)

        row_report_totals = self.get_empty_row_asdict(self.report_totals, [])
        for grouper, resources in g:
            rows = list()
            row_group_totals = self.get_empty_row_asdict(self.group_totals, [])
            for resource in resources:
                row = ReportRow()
                if isinstance(resource, (tuple, list)):
                    for index, value in enumerate(resource):
                        if ffields[index] in self.group_totals:
                            row_group_totals[ffields[index]].append(value)
                        elif ffields[index] in self.report_totals:
                            row_report_totals[ffields[index]].append(value)
                        value = self._get_value_text(index, value)
                        value = ReportValue(value)
                        if ffields[index] in self.override_field_values:
                            value.to_value = self.override_field_values[ffields[index]]
                        if ffields[index] in self.override_field_formats:
                            value.format = self.override_field_formats[ffields[index]]
                        row.append(value)
                else:
                    for index, column in enumerate(ffields):
                        value = get_field_value(resource, column)
                        if ffields[index] in self.group_totals:
                            row_group_totals[ffields[index]].append(value)
                        elif ffields[index] in self.report_totals:
                            row_report_totals[ffields[index]].append(value)
                        value = self._get_value_text(index, value)
                        value = ReportValue(value)
                        if column in self.override_field_values:
                            value.to_value = self.override_field_values[column]
                        if column in self.override_field_formats:
                            value.format = self.override_field_formats[column]
                        row.append(value)
                rows.append(row)
            if row_group_totals:
                if groupby_data['groupby']:
                    header_group_total = compute_row_header(self.group_totals)
                    row = compute_row_totals(self.group_totals, row_group_totals, is_group_total=True)
                    rows.append(header_group_total)
                    rows.append(row)
                for k, v in row_group_totals.items():
                    if k in row_report_totals:
                        row_report_totals[k].extend(v)

            if groupby_data and groupby_data['groupby']:
                grouper = self._get_grouper_text(groupby_data['groupby'], grouper)
            else:
                grouper = None
            if isinstance(grouper, (list, tuple)):
                grouper = grouper[0]
            report_rows.append([grouper, rows])
        if self.has_report_totals():
            header_report_total = compute_row_header(self.report_totals)
            row = compute_row_totals(self.report_totals, row_report_totals, is_report_total=True)
            header_report_total.is_report_totals = True
            row.is_report_totals = True
            report_rows.append([_('Totals'), [header_report_total, row]])

        return report_rows


reports.register('osszesito', SummaryList)
