from django import forms
from django.forms import MultipleChoiceField
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.contrib.auth.models import User
from django_messages.models import Message

from rovidtav.admin_helpers import get_recipient_choices
from django.db.utils import OperationalError

if "notification" in settings.INSTALLED_APPS and getattr(settings, 'DJANGO_MESSAGES_NOTIFY', True):
    from notification import models as notification
else:
    notification = None


class ComposeForm(forms.Form):
    """
    A simple default form for private messages.
    """
    try:
        user_choices = [(u.pk, u.username) for u in User.objects.all()]
    except OperationalError:
        user_choices = []
    recipient = MultipleChoiceField(
        label=_(u"Recipient"), choices=get_recipient_choices())
    subject = forms.CharField(label=_(u"Subject"), max_length=140)
    body = forms.CharField(
        label=_(u"Body"),
        widget=forms.Textarea(attrs={'rows': '12', 'cols': '55'}))

    def __init__(self, *args, **kwargs):
        recipient_filter = kwargs.pop('recipient_filter', None)
        super(ComposeForm, self).__init__(*args, **kwargs)
        if recipient_filter is not None:
            self.fields['recipient']._recipient_filter = recipient_filter
        self.fields['recipient'].choices = get_recipient_choices()

    def save(self, sender, parent_msg=None):
        recipients = self.cleaned_data['recipient']
        subject = self.cleaned_data['subject']
        body = self.cleaned_data['body']
        message_list = []
        for r in recipients:
            rec_user = User.objects.get(pk=r)
            msg = Message(
                sender=sender,
                recipient=rec_user,
                subject=subject,
                body=body,
            )
            if parent_msg is not None:
                msg.parent_msg = parent_msg
                parent_msg.replied_at = timezone.now()
                parent_msg.save()
            msg.save()
            message_list.append(msg)
            if notification:
                if parent_msg is not None:
                    notification.send([sender],
                                      "messages_replied",
                                      {'message': msg})
                    notification.send([rec_user],
                                      "messages_reply_received",
                                      {'message': msg})
                else:
                    notification.send([sender],
                                      "messages_sent",
                                      {'message': msg})
                    notification.send([rec_user],
                                      "messages_received",
                                      {'message': msg})
        return message_list


try:
    class ComposeFormAllUsers(ComposeForm):
        recipient = MultipleChoiceField(
            label=_(u"Recipient"),
            choices=[(u.pk, u.username) for u in User.objects.all()])
except OperationalError:
    class ComposeFormAllUsers(ComposeForm):
        pass
