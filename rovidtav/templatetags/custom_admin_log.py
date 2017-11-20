from django import template
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType

from rovidtav.models import Note

register = template.Library()


class CustomAdminLogNode(template.Node):
    def __init__(self, limit, varname, user):
        self.limit, self.varname, self.user = limit, varname, user

    def __repr__(self):
        return "<GetAdminLog Node>"

    def render(self, context):
        ct = ContentType.objects.get_for_model(Note)
        if self.user is None:
            entries = LogEntry.objects.filter(content_type=ct)
        else:
            user_id = self.user
            if not user_id.isdigit():
                user_id = context[self.user].pk
            entries = LogEntry.objects.filter(user__pk=user_id, content_type=ct)
        context[self.varname] = entries.select_related('content_type', 'user')[:int(self.limit)]
        return ''


@register.tag
def get_custom_admin_log(parser, token):
    """
    Populate a template variable with the admin log for the given criteria.

    Usage::

        {% get_admin_log [limit] as [varname] for_user [context_var_containing_user_obj] %}

    Examples::

        {% get_admin_log 10 as admin_log for_user 23 %}
        {% get_admin_log 10 as admin_log for_user user %}
        {% get_admin_log 10 as admin_log %}

    Note that ``context_var_containing_user_obj`` can be a hard-coded integer
    (user ID) or the name of a template context variable containing the user
    object whose ID you want.
    """
    tokens = token.contents.split()
    if len(tokens) < 4:
        raise template.TemplateSyntaxError(
            "'get_admin_log' statements require two arguments")
    if not tokens[1].isdigit():
        raise template.TemplateSyntaxError(
            "First argument to 'get_admin_log' must be an integer")
    if tokens[2] != 'as':
        raise template.TemplateSyntaxError(
            "Second argument to 'get_admin_log' must be 'as'")
    if len(tokens) > 4:
        if tokens[4] != 'for_user':
            raise template.TemplateSyntaxError(
                "Fourth argument to 'get_admin_log' must be 'for_user'")
    return CustomAdminLogNode(limit=tokens[1], varname=tokens[3], user=(tokens[5] if len(tokens) > 5 else None))
