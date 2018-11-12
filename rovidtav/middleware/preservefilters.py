from django import http
from django.http import Http404
from django.core import urlresolvers
from urlparse import urlparse


class PreserveFilters(object):
    """
    The purpose of this middleware is to automatically save the values of all filters for each
    admin changelist page so that when a user leaves a changelist page request and then comes
    back to it, the filter is still there.
    This middleware must come after the session middleware.
    Add this middleware to MIDDLEWARE_CLASSES in your settings.py
    This middleware will then automatically save the values of all filters in the admin changelist
    for all models.
    """

    def process_request(self, request):
        """
        """

        try:
            current_url = urlresolvers.resolve(request.path)
        except Http404:
            return

        if not current_url.namespace == 'admin' or \
           not current_url.view_name.endswith('_changelist'):
            return

        referer_parsed = urlparse(unicode(request.META.get("HTTP_REFERER", None)))

        if request.path == referer_parsed.path:
            # save session and return if the same page has been submitted.
            request.session[current_url.view_name] = unicode(request.META.get('QUERY_STRING', None))
            return
        else:
            admin_session = request.session.get(current_url.view_name, None)
            q = unicode(request.META.get('QUERY_STRING', None))
            if admin_session and admin_session == q:
                return
            elif admin_session and not q.strip():
                return
            elif admin_session:
                new_url = request.path + '?' + admin_session
                return http.HttpResponsePermanentRedirect(new_url)

        return
