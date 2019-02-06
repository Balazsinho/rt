"""rovidtav URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import url

from rovidtav.api.v1.views import (create_ticket, add_ticket_attachment,
                                   download_attachment, download_thumbnail,
                                   download_ntattachment, download_ntthumbnail,
                                   download_mmattachment, download_mmthumbnail,
                                   email_stats, create_uninstall_ticket,
                                   download_uninstattachment,
                                   download_uninstthumbnail)


urlpatterns = [
    url(r'^ticket/create', create_ticket),
    url(r'^ticket/attachment', add_ticket_attachment),
    url(r'^uninstall_ticket/create', create_uninstall_ticket),
    url(r'^attachment/(?P<attachment_id>\d+)$', download_attachment),
    url(r'^thumbnail/(?P<attachment_id>\d+)$', download_thumbnail),
    url(r'^ntattachment/(?P<attachment_id>\d+)$', download_ntattachment),
    url(r'^ntthumbnail/(?P<attachment_id>\d+)$', download_ntthumbnail),
    url(r'^mmattachment/(?P<attachment_id>\d+)$', download_mmattachment),
    url(r'^mmthumbnail/(?P<attachment_id>\d+)$', download_mmthumbnail),
    url(r'^uninstattachment/(?P<attachment_id>\d+)$', download_uninstattachment),
    url(r'^uninstthumbnail/(?P<attachment_id>\d+)$', download_uninstthumbnail),
    url(r'^email_stats$', email_stats),
]
