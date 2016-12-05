# -*- coding: utf-8 -*-

import json

from PIL import Image
import StringIO

from rest_framework.authentication import (SessionAuthentication,
                                           BasicAuthentication)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from rest_framework.decorators import api_view
from rest_framework.decorators import authentication_classes
from rest_framework.decorators import permission_classes

from rovidtav.settings import IMAGE_THUMB_PX
from rovidtav.api.field_const import Fields
from rovidtav.models import (Client, City, Ticket, TicketType,
                             Note, DeviceType, Device, Attachment,
                             DeviceOwner)
from django.http.response import HttpResponse


def _error(data):
    content = {'error': data}
    return Response(json.dumps(content))


@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def create_ticket(request):
    req_keys = (Fields.CITY, Fields.ZIP, Fields.STREET, Fields.HOUSE_NUM,
                Fields.NAME1, Fields.PHONE1, Fields.MT_ID, Fields.TASK_TYPE,
                Fields.TICKET_ID)

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
        client = Client.objects.create(
            mt_id=mt_id,
            name=data[Fields.NAME1],
            city=city,
            address=addr,
            phone=data[Fields.PHONE1],
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
                    name=device[Fields.DEV_TYPE])
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

    return Response(json.dumps({'ticket_id': ticket.pk}))


@api_view(['POST'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def add_ticket_attachment(request):
    pass


@api_view(['GET'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def download_attachment(request, attachment_id):
    try:
        att = Attachment.objects.get(pk=attachment_id)
        return HttpResponse(
            att.data,
            content_type=att.content_type,
        )
    except Attachment.DoesNotExist:
        return Response(json.dumps({'error': 'File not found'}))


@api_view(['GET'])
@authentication_classes((SessionAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def download_thumbnail(request, attachment_id):
    try:
        att = Attachment.objects.get(pk=attachment_id)

        if att.is_image():
            temp_buff = StringIO.StringIO()
            temp_buff.write(att.data)
            temp_buff.seek(0)

            img = Image.open(temp_buff)
            img.thumbnail((IMAGE_THUMB_PX, IMAGE_THUMB_PX), Image.ANTIALIAS)
            temp_buff = StringIO.StringIO()
            temp_buff.name = att.name
            img.save(temp_buff)
            temp_buff.seek(0)

            return HttpResponse(
                temp_buff.read(),
                content_type=att.content_type,
            )
        else:
            return HttpResponse('')
    except Attachment.DoesNotExist:
        return Response(json.dumps({'error': 'File not found'}))
