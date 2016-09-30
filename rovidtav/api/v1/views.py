# -*- coding: utf-8 -*-

import json

from rest_framework.authentication import (SessionAuthentication,
                                           BasicAuthentication)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from rest_framework.decorators import api_view
from rest_framework.decorators import authentication_classes
from rest_framework.decorators import permission_classes

from rovidtav.api.field_const import Fields
from rovidtav.models import (Client, City, Ticket, TicketType,
                             TicketEvent, DeviceType, Device, Attachment)
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
    data = json.loads(unicode(request.read(), 'iso-8859-1'))

    if not all(key in data for key in req_keys):
        missing_keys = list(set(req_keys) - set(data.keys()))
        return _error({'missing_keys': missing_keys})

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

    ticket_type, _ = TicketType.objects.get_or_create(
        name=(data[Fields.TASK_TYPE]))
    ticket = Ticket.objects.create(
        ext_id=data[Fields.TICKET_ID],
        client=client,
        ticket_type=ticket_type,
        city=city,
        address=addr,
        created_by=request.user,
    )

    if Fields.REMARKS in data and data[Fields.REMARKS]:
        TicketEvent.objects.create(
            ticket=ticket,
            event='Megj',
            remark=data[Fields.REMARKS],
            created_by=request.user,
        )

    if Fields.COLLECTABLE_MONEY in data and data[Fields.COLLECTABLE_MONEY]:
        TicketEvent.objects.create(
            ticket=ticket,
            event='Megj',
            remark=u'Beszedés {}'.format(data[Fields.COLLECTABLE_MONEY]),
            created_by=request.user,
        )

    if Fields.DEVICES in data:
        for device in data[Fields.DEVICES]:
            dev_type, _ = DeviceType.objects.get_or_create(
                name=device[Fields.DEV_TYPE])
            dev = Device.objects.create(
                sn=device[Fields.DEV_SN],
                type=dev_type,
            )
            if device.get(Fields.DEV_CARD_SN):
                dev_type, _ = DeviceType.objects.get_or_create(
                    name='SMART CARD')
                card = Device.objects.create(
                    sn=device[Fields.DEV_CARD_SN],
                    type=dev_type,
                    connected_device=dev,
                )

    if 'html' in data:
        Attachment.objects.create(
            ticket=ticket,
            name='Hibajegy.html',
            _data=data['html'].encode('iso-8859-1').replace('\\"', '"'),
            remark='A matávtól érkezett eredeti hibajegy',
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
