# -*- coding: utf-8 -*-

from django.forms.fields import DateField, ChoiceField

from model_report.report import reports

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


reports.register('osszesito', SummaryList)
