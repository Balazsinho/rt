"""
From
https://gist.github.com/mindlace/3918300
"""

from django.db.models import signals
from django.utils.functional import curry


class WhoDidWhat(object):
    def process_request(self, request):
        if request.method not in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            if hasattr(request, 'user') and request.user.is_authenticated():
                user = request.user
            else:
                user = None

            mark_whodid = curry(self.mark_whodid, user)
            signals.pre_save.connect(mark_whodid,
                                     dispatch_uid=(self.__class__, request,),
                                     weak=False)

    def process_response(self, request, response):
        signals.pre_save.disconnect(dispatch_uid=(self.__class__, request,))
        return response

    def mark_whodid(self, user, sender, instance, **kwargs):
        if hasattr(instance, 'created_by_id') and \
                not getattr(instance, 'created_by_id', None):
            instance.created_by = user
        if hasattr(instance, 'modified_by_id'):
            instance.modified_by = user
