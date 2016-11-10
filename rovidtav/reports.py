# -*- coding: utf-8 -*-

from rovidtav.models import Ticket
from model_report.report import reports, ReportAdmin


class SummaryList(ReportAdmin):
    title = u'Összesítő lista'
    model = Ticket
    fields = [
        'ext_id',
        'address',
    ]
    list_order_by = ('ext_id',)
    type = 'report'


reports.register('osszesito', SummaryList)
