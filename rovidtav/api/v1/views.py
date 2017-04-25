# -*- coding: utf-8 -*-

import json
import codecs
import os

from PIL import Image, ExifTags
import StringIO

from rest_framework.authentication import (SessionAuthentication,
                                           BasicAuthentication)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from rest_framework.decorators import api_view
from rest_framework.decorators import authentication_classes
from rest_framework.decorators import permission_classes

from rovidtav.settings import IMAGE_THUMB_PX, STATIC_ROOT
from rovidtav.api.field_const import Fields
from rovidtav.models import (Client, City, Ticket, TicketType,
                             Note, DeviceType, Device, Attachment,
                             DeviceOwner, SystemEmail, Const, NTAttachment)
from django.http.response import HttpResponse


def _error(data):
    return Response({'error': data})


@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def create_ticket(request):
    req_keys = (Fields.CITY, Fields.ZIP, Fields.STREET, Fields.HOUSE_NUM,
                Fields.NAME1, Fields.MT_ID, Fields.TASK_TYPE, Fields.TICKET_ID,
                )  # Fields.PHONE1)

    # data = json.loads(unicode(request.read(), 'latin-1').encode('utf-8'))
    data = json.loads(request.read())

    if not all(key in data for key in req_keys):
        missing_keys = list(set(req_keys) - set(data.keys()))
        return _error({'missing_keys': missing_keys})

    try:
        Ticket.objects.get(ext_id=data[Fields.TICKET_ID])
        return _error('duplicate ticket: {}'.format(data[Fields.TICKET_ID]))
    except Ticket.DoesNotExist:
        pass
    except Ticket.MultipleObjectsReturned:
        return _error('duplicate ticket;'
                      ' multiple tickets with id {}'
                      ''.format(data[Fields.TICKET_ID]))

    city, _ = City.objects.get_or_create(
        name=data[Fields.CITY],
        zip=int(data[Fields.ZIP]),
    )

    mt_id = data[Fields.MT_ID]
    addr = u'{} {}'.format(data[Fields.STREET],
                           data[Fields.HOUSE_NUM])

    try:
        client = Client.objects.get(mt_id=mt_id)
    except Client.DoesNotExist:
        phone1 = data.get(Fields.PHONE1, u'')
        client = Client.objects.create(
            mt_id=mt_id,
            name=data[Fields.NAME1],
            city=city,
            address=addr,
            phone=phone1,
            created_by=request.user,
        )

    ticket_types = []
    if data.get(Fields.TASK_TYPE_LIST):
        for t in data[Fields.TASK_TYPE_LIST]:
            ticket_type, _ = TicketType.objects.get_or_create(name=t)
            ticket_types.append(ticket_type)
    else:
        ticket_type, _ = TicketType.objects.get_or_create(
            name=data[Fields.TASK_TYPE])
        ticket_types.append(ticket_type)

    ticket = Ticket.objects.create(
        ext_id=data[Fields.TICKET_ID],
        client=client,
        city=city,
        address=addr,
        created_by=request.user,
        created_at=data['mail_date'],
    )

    ticket.ticket_types.add(*ticket_types)

    if Fields.REMARKS in data and data[Fields.REMARKS]:
        Note.objects.create(
            content_object=ticket,
            is_history=False,
            remark=data[Fields.REMARKS],
            created_by=request.user,
        )

    if Fields.COLLECTABLE_MONEY in data and data[Fields.COLLECTABLE_MONEY]:
        Note.objects.create(
            content_object=ticket,
            is_history=False,
            remark=u'Beszedés {}'.format(data[Fields.COLLECTABLE_MONEY]),
            created_by=request.user,
        )
        ticket[Ticket.Keys.COLLECTABLE_MONEY] = data[Fields.COLLECTABLE_MONEY]

    if Fields.DEVICES in data:
        for device in data[Fields.DEVICES]:
            try:
                dev = Device.objects.get(
                    sn=device[Fields.DEV_SN])
            except Device.DoesNotExist:
                dev_type, _ = DeviceType.objects.get_or_create(
                    name=(device[Fields.DEV_TYPE] or '').strip())
                dev = Device.objects.create(
                    sn=device[Fields.DEV_SN],
                    type=dev_type,
                    card_sn=device.get(Fields.DEV_CARD_SN),
                )
                DeviceOwner.objects.create(device=dev,
                                           content_type=client.get_content_type_obj(),
                                           object_id=client.pk)
            except Device.MultipleObjectsReturned:
                # Handle error, now just leave it, probably some old
                # inconsistency
                pass

    if 'html' in data:
        Attachment.objects.create(
            ticket=ticket,
            name='Hibajegy.html',
            _data=data['html'].encode('utf-8'),
            remark='A matávtól érkezett eredeti hibajegy',
            created_by=request.user,
        )

    for att_name, att_content in data['attachments'].iteritems():
        Attachment.objects.create(
            ticket=ticket,
            name=att_name,
            _data=att_content,
            created_by=request.user,
        )

    return Response({'ticket_id': ticket.pk})


@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def add_ticket_attachment(request):
    req_keys = (Fields.TICKET_ID, 'attachment_name', 'attachment_content')
    data = json.loads(request.read())
    if not all(key in data for key in req_keys):
        missing_keys = list(set(req_keys) - set(data.keys()))
        return _error({'missing_keys': missing_keys})

    try:
        ticket = Ticket.objects.get(ext_id=data['ticket_id'])
    except Ticket.DoesNotExist:
        return _error('Ticket {} does not exist'.format(data['ticket_id']))

    Attachment.objects.create(
        ticket=ticket,
        name=data['attachment_name'],
        _data=data['attachment_content'],
        created_by=request.user,
    )
    return Response({'OK': 'Done'})


def _download_from_model(model, pk):
    try:
        att = model.objects.get(pk=pk)
        return HttpResponse(
            att.data,
            content_type=att.content_type,
        )
    except model.DoesNotExist:
        return _error('File not found')


def _thumbnail_from_model(model, pk):
    try:
        att = model.objects.get(pk=pk)

        if att.is_image():
            temp_buff = StringIO.StringIO()
            temp_buff.write(att.data)
            temp_buff.seek(0)

            img = Image.open(temp_buff)
            img.thumbnail((IMAGE_THUMB_PX, IMAGE_THUMB_PX), Image.ANTIALIAS)
            temp_buff = StringIO.StringIO()
            temp_buff.name = att.name
            exif = {
                ExifTags.TAGS[k]: v
                for k, v in (img._getexif() or {}).items()
                if k in ExifTags.TAGS
            }
            orientation = exif.get('Orientation')
            if orientation == 6:
                img = img.rotate(-90, expand=True)
            elif orientation == 8:
                img = img.rotate(90, expand=True)
            img.save(temp_buff)
            temp_buff.seek(0)
            return HttpResponse(temp_buff.read(),
                                content_type=att.content_type)

        else:
            with codecs.open(os.path.join(STATIC_ROOT, 'images',
                                          'document-icon.png')) as icon:
                img = Image.open(icon)
                temp_buff = StringIO.StringIO()
                temp_buff.name = att.name + '.png'
                img.thumbnail((100, 100), Image.ANTIALIAS)
                img.save(temp_buff)
                temp_buff.seek(0)

            return HttpResponse(temp_buff.read(), content_type='image/png')
    except model.DoesNotExist:
        return _error('File not found')


@api_view(['GET'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def download_attachment(request, attachment_id):
    return _download_from_model(Attachment, attachment_id)


@api_view(['GET'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def download_thumbnail(request, attachment_id):
    return _thumbnail_from_model(Attachment, attachment_id)


@api_view(['GET'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def download_ntattachment(request, attachment_id):
    return _download_from_model(NTAttachment, attachment_id)


@api_view(['GET'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def download_ntthumbnail(request, attachment_id):
    return _thumbnail_from_model(NTAttachment, attachment_id)


@api_view(['GET'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def email_stats(request):
    try:
        emails = SystemEmail.objects.all()
        total = len(emails)
        errors = len(emails.filter(status=Const.EmailStatus.ERROR))
        sent = len(emails.filter(status=Const.EmailStatus.SENT))
        fixed = len(emails.filter(status=Const.EmailStatus.FIXED))
        in_progress = len(emails.filter(status=Const.EmailStatus.IN_PROGRESS))
        return Response({
            'total': total,
            'errors': errors,
            'sent': sent,
            'fixed': fixed,
            'in_progress': in_progress
        })
    except Exception as e:
        return Response({'error': e})
