# -*- coding: utf-8 -*-
from django.shortcuts import render_to_response
from django.http import Http404

from model_report.report import reports


def report_list(request):
    """
    This view render all reports registered
    """
    context = {
        'report_list': reports.get_reports(),
        'user': request.user,
        'request': request,
    }
    return render_to_response('model_report/report_list.html', context)


def report(request, slug):
    """
    This view render one report

    Keywords arguments:

    slug -- slug of the report
    """
    report_class = reports.get_report(slug)
    if not report_class:
        raise Http404
    context = {
        'report_list': reports.get_reports(),
        'user': request.user,
        'request': request,
    }

    report = report_class(request=request)
    return report.render(request, extra_context=context)
