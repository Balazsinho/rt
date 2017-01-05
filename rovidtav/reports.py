# -*- coding: utf-8 -*-
from django.forms.fields import ChoiceField

from model_report.report import reports

from rovidtav.report_helpers import CustomReportAdmin, Label
from rovidtav.models import Ticket
from _collections import defaultdict


def to_date(dt, instance=None):
    if dt:
        return dt.strftime('%Y-%m-%d')
    return ''


class SummaryList(CustomReportAdmin):

    title = u'Összesítő lista'
    model = Ticket
    fields = [
        'ext_id',
        'client__mt_id',
        'client__name',
        'city__name',
        'address',
        'city__primer',
        'owner__username',
        'closed_at',
        'payoff__name'
    ]

    list_filter = ['owner', 'payoff__name', 'city__primer', 'created_at', 'closed_at']
    list_filter_classes = {
        'city__primer': ChoiceField,
        'payoff__name': ChoiceField,
    }
    list_order_by = ('-created_at',)
    type = 'report'
    override_field_labels = {
        'owner__username': Label(u'Szerelő'),
        'payoff__name': Label(u'Elszámolás'),
        'created_at': Label(u'Felvéve'),
        'closed_at': Label(u'Lezárva'),
        'city__name': Label(u'Település'),
    }
    override_field_formats = {
        'closed_at': to_date,
    }
    extra_columns_first_col = 5

    def get_form_filter(self, request):
        self._check_admin_user(request)
        if self.data_owner:
            self.list_filter = [f for f in self.list_filter if f not in ('owner',)]
        return CustomReportAdmin.get_form_filter(self, request)

    def _calc_extra_from_qs(self, qs):
        if not hasattr(self, 'calculated_columns'):
            workitem_keys = set()
            material_keys = set()
            id_extra_map = defaultdict(dict)
            for ticket in qs:
                tws = ticket.munka_jegy.all()
                workitem_keys |= set([tw.work_item for tw in tws])
                id_extra_map[ticket.pk].update(dict([(tw.work_item.art_number, tw.amount) for tw in tws]))
                price = sum([tw.work_item.art_price * tw.amount for tw in tws])
                if id_extra_map[ticket.pk]:
                    id_extra_map[ticket.pk][u'Ár összesen'] = int(price)

                tms = ticket.anyag_jegy.all()
                material_keys |= set([tm.material for tm in tms])
                id_extra_map[ticket.pk].update(dict([(tm.material.sn, tm.amount) for tm in tms]))

            workitem_keys = sorted(list(workitem_keys), key=lambda x: x.art_number)
            material_keys = sorted(list(material_keys), key=lambda x: x.sn)
            wo_offsets = list(enumerate(workitem_keys + material_keys))
            self.calculated_columns = [(e[0]+self.extra_columns_first_col, e[1].art_number if hasattr(e[1], 'art_number') else e[1].sn) for e in wo_offsets]
            self.calculated_columns.append((len(self.calculated_columns + self.fields), u'Ár összesen'))
            self.extra_col_map = id_extra_map
            self.id_url_map = dict([(t.ext_id, '/admin/rovidtav/ticket/{}/change'.format(t.pk)) for t in qs])

    def get_render_context(self, request, extra_context={}, by_row=None):
        ctx = super(SummaryList, self).get_render_context(
            request, extra_context, by_row)
        ctx['id_url_map'] = self.id_url_map
        return ctx


reports.register('osszesito', SummaryList)
