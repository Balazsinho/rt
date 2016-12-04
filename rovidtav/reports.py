# -*- coding: utf-8 -*-
from django.forms.fields import ChoiceField

from model_report.report import reports

from rovidtav.report_helpers import CustomReportAdmin, Label
from rovidtav.models import Ticket


def to_date(dt, instance=None):
    if dt:
        return dt.strftime('%Y-%m-%d')
    return ''


class SummaryList(CustomReportAdmin):

    title = u'Összesítő lista'
    model = Ticket
    fields = [
        'ext_id',
        'city__name',
        'address',
        'city__primer',
        'owner__username',
        'closed_at',
    ]

    list_filter = ('city__primer', 'owner', 'closed_at')
    list_filter_classes = {
        'city__primer': ChoiceField,
    }
    list_order_by = ('ext_id',)
    type = 'report'
    override_field_labels = {
        'owner__username': Label(u'Tulajdonos'),
        'closed_at': Label(u'Lezárva'),
    }
    override_field_formats = {
        'closed_at': to_date,
    }
    extra_columns_first_col = 4

    def _calc_extra_from_qs(self, qs):
        if not hasattr(self, 'calculated_columns'):
            workitem_keys = set()
            id_workitem_map = {}
            for ticket in qs:
                tws = ticket.munka_jegy.all()
                workitem_keys |= set([tw.work_item for tw in tws])
                id_workitem_map[ticket.pk] = dict([(tw.work_item.art_number, tw.amount) for tw in tws])
                price = sum([tw.work_item.given_price * tw.amount for tw in tws])
                if id_workitem_map[ticket.pk]:
                    id_workitem_map[ticket.pk][u'Ár összesen'] = price

            workitem_keys = sorted(list(workitem_keys))
            wo_offsets = list(enumerate(workitem_keys))
            self.calculated_columns = [(e[0]+self.extra_columns_first_col, e[1].art_number) for e in wo_offsets]
            self.calculated_columns.append((len(self.calculated_columns + self.fields), u'Ár összesen'))
            self.extra_col_map = id_workitem_map


reports.register('osszesito', SummaryList)
