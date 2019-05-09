# -*- coding: utf-8 -*-
from django.forms.fields import ChoiceField

from model_report.report import reports

from rovidtav.report_helpers import CustomReportAdmin, Label, DedupedReportRows
from rovidtav.models import Ticket, Note, NetworkTicket, IndividualWorkItem,\
    NTNEWorkItem, NTNEMaterial
from _collections import defaultdict


def to_date(dt, instance=None):
    if dt:
        return dt.strftime('%Y-%m-%d')
    return ''


def to_status_str(status, instance=None):
    status_dict = dict((
        (0, u'Ellenőrizendő'),
        (1, u'Vizsgálva - OK'),
        (2, u'Javítandó'),
        (3, u'Javítva'),))
    if status:
        return status_dict.get(status, status)
    return ''


class SummaryList(CustomReportAdmin):

    title = u'Összesítő lista'
    model = Ticket
    fields = [
        'ext_id',
        'client__mt_id',
        'client__name',
        'city__name',
        'address',
        'city__primer',
        'owner__username',
        'closed_at',
        'payoffs'
    ]

    list_filter = ['owner', 'payoffs', 'city__primer', 'ticket_tags', 'created_at', 'closed_at']
    list_filter_classes = {
        'city__primer': ChoiceField,
    }
    list_order_by = ('-created_at',)
    type = 'report'
    override_field_labels = {
        'owner__username': Label(u'Szerelő'),
        #'payoffs': Label(u'Elszámolás'),
        'created_at': Label(u'Felvéve'),
        'closed_at': Label(u'Lezárva'),
        'city__name': Label(u'Település'),
    }
    override_field_formats = {
        'closed_at': to_date,
    }
    extra_columns_first_col = 5

    def get_form_filter(self, request):
        self._check_admin_user(request)
        if self.data_owner:
            self.list_filter = [f for f in self.list_filter if f not in ('owner',)]
        return CustomReportAdmin.get_form_filter(self, request)

    def _calc_extra_from_qs(self, qs):
        workitem_keys = set()
        material_keys = set()
        id_extra_map = defaultdict(dict)
        for ticket in qs:
            tws = ticket.munka_jegy.all()
            workitem_keys |= set([tw.work_item for tw in tws])
            id_extra_map[ticket.pk].update(dict([(tw.work_item.art_number, tw.amount) for tw in tws]))
            price = sum([tw.work_item.art_price * tw.amount for tw in tws])
            if id_extra_map[ticket.pk]:
                id_extra_map[ticket.pk][u'Ár összesen'] = int(price)

            tms = ticket.anyag_jegy.all()
            material_keys |= set([tm.material for tm in tms])
            id_extra_map[ticket.pk].update(dict([(tm.material.sn, tm.amount) for tm in tms]))

            # Elszamolasok
            payoffs = ', '.join([str(t) for t in ticket.payoffs.all()])
            id_extra_map[ticket.pk][u'Elszámolás'] = payoffs

        workitem_keys = sorted(list(workitem_keys), key=lambda x: x.art_number)
        material_keys = sorted(list(material_keys), key=lambda x: x.sn)
        wo_offsets = list(enumerate(workitem_keys + material_keys))
        self.calculated_columns = [(e[0]+self.extra_columns_first_col, e[1].art_number if hasattr(e[1], 'art_number') else e[1].sn) for e in wo_offsets]
        self.calculated_columns.insert(0, (self.extra_columns_first_col-1, u'Elszámolás'))
        self.calculated_columns.append((len(self.calculated_columns + self.fields), u'Ár összesen'))
        self.extra_col_map = id_extra_map
        self.id_url_map = dict([(t.ext_id, '/admin/rovidtav/ticket/{}/change'.format(t.pk)) for t in qs])

    def get_render_context(self, request, extra_context={}, by_row=None):
        ctx = super(SummaryList, self).get_render_context(
            request, extra_context, by_row)
        ctx['id_url_map'] = self.id_url_map
        return ctx


class OnDemandList(CustomReportAdmin):

    title = u'Lista cimkék alapján'
    model = Ticket
    fields = [
        'ext_id',
        'client__mt_id',
        'client__name',
        'city__name',
        'address',
        'remark',
        'status',
        'owner__username',
        'created_at',
        'closed_at',
    ]

    list_filter = ['ticket_tags', 'owner', 'created_at', 'closed_at']
    list_order_by = ('-created_at',)
    type = 'report'
    override_field_labels = {
        'owner__username': Label(u'Szerelő'),
        'created_at': Label(u'Felvéve'),
        'closed_at': Label(u'Lezárva'),
        'city__name': Label(u'Település'),
    }
    override_field_formats = {
        'closed_at': to_date,
        'created_at': to_date,
    }
    extra_columns_first_col = 10

    def _calc_extra_from_qs(self, qs):
        remark_key = u'megjegyzés_'
        history_key = u'történet_'

        id_extra_map = defaultdict(dict)
        for ticket in qs:
            notes = Note.objects.filter(content_type=ticket.get_content_type(),
                                        object_id=ticket.pk,
                                        is_history=False)
            for idx, note in enumerate(notes):
                note_txt = u'{} ({}) - {}'.format(note.created_by.username,
                                                  to_date(note.created_at),
                                                  note.remark)
                id_extra_map[ticket.pk][remark_key+str(idx+1)] = note_txt
            history = Note.objects.filter(content_type=ticket.get_content_type(),
                                          object_id=ticket.pk,
                                          is_history=True)
            for idx, note in enumerate(history):
                note_txt = u'{} ({}) - {}'.format(note.created_by.username,
                                                  to_date(note.created_at),
                                                  note.remark)
                id_extra_map[ticket.pk][history_key+str(idx+1)] = note_txt

        self.calculated_columns = []
        for ticket_cols in id_extra_map.values():
            cols = ticket_cols.keys()
            for col in cols:
                if col not in self.calculated_columns:
                    self.calculated_columns.append(col)
        self.calculated_columns.sort()
        self.calculated_columns = [(idx+self.extra_columns_first_col, col)
                                   for idx, col
                                   in enumerate(self.calculated_columns)]
        self.extra_col_map = id_extra_map
        self.id_url_map = dict([(t.ext_id, '/admin/rovidtav/ticket/{}/change'.format(t.pk)) for t in qs])

    def get_render_context(self, request, extra_context={}, by_row=None):
        ctx = super(OnDemandList, self).get_render_context(
            request, extra_context, by_row)
        ctx['id_url_map'] = self.id_url_map
        return ctx


class OnDemandNetworkTicketList(CustomReportAdmin):

    title = u'Hálózati jegy lista cimkék alapján'
    model = NetworkTicket
    fields = [
        'city__name',
        'address',
        'onu',
        'status',
        'created_at',
        'closed_at',
    ]

    list_filter = ['ticket_tags', 'owner', 'created_at', 'closed_at']
    list_order_by = ('-created_at',)
    type = 'report'
    override_field_labels = {
        'created_at': Label(u'Felvéve'),
        'closed_at': Label(u'Lezárva'),
        'city__name': Label(u'Település'),
    }
    override_field_formats = {
        'closed_at': to_date,
        'created_at': to_date,
    }
    extra_columns_first_col = 6

    def _calc_extra_from_qs(self, qs):
        remark_key = u'megjegyzés_'
        history_key = u'történet_'

        id_extra_map = defaultdict(dict)
        for ticket in qs:
            notes = Note.objects.filter(content_type=ticket.get_content_type(),
                                        object_id=ticket.pk,
                                        is_history=False)
            for idx, note in enumerate(notes):
                note_txt = u'{} ({}) - {}'.format(note.created_by.username,
                                                  to_date(note.created_at),
                                                  note.remark)
                id_extra_map[ticket.pk][remark_key+str(idx+1)] = note_txt
            history = Note.objects.filter(content_type=ticket.get_content_type(),
                                          object_id=ticket.pk,
                                          is_history=True)
            for idx, note in enumerate(history):
                note_txt = u'{} ({}) - {}'.format(note.created_by.username,
                                                  to_date(note.created_at),
                                                  note.remark)
                id_extra_map[ticket.pk][history_key+str(idx+1)] = note_txt

            id_extra_map[ticket.pk][u'Szerelő'] = u', '.join([u.username for u in ticket.owner.all()])

        self.calculated_columns = [u'Szerelő']
        for ticket_cols in id_extra_map.values():
            cols = ticket_cols.keys()
            for col in cols:
                if col not in self.calculated_columns:
                    self.calculated_columns.append(col)
        self.calculated_columns.sort()
        self.calculated_columns = [(idx+self.extra_columns_first_col, col)
                                   for idx, col
                                   in enumerate(self.calculated_columns)]
        self.extra_col_map = id_extra_map
        self.id_url_map = dict([(t.address, '/admin/rovidtav/networkticket/{}/change'.format(t.pk)) for t in qs])

    def get_render_context(self, request, extra_context={}, by_row=None):
        ctx = super(OnDemandNetworkTicketList, self).get_render_context(
            request, extra_context, by_row)
        ctx['id_url_map'] = self.id_url_map
        return ctx


class NetworkTicketSummaryList(CustomReportAdmin):

    title = u'Hálózati jegy összesítő lista'
    model = NetworkTicket
    fields = [
        'address',
        'city__name',
        'onu',
        'status',
        'created_at',
        'closed_at',
    ]

    list_filter = ['owner', 'city__name', 'onu', 'created_at', 'closed_at']
    list_filter_classes = {
        'city__name': ChoiceField,
        'onu': ChoiceField,
    }
    list_order_by = ('-created_at',)
    type = 'report'
    override_field_labels = {
        'owner__username': Label(u'Szerelő'),
        'created_at': Label(u'Felvéve'),
        'closed_at': Label(u'Lezárva'),
        'city__name': Label(u'Település'),
    }
    override_field_formats = {
        'closed_at': to_date,
        'created_at': to_date,
    }
    extra_columns_first_col = 6

    def get_form_filter(self, request):
        self._check_admin_user(request)
        if self.data_owner:
            self.list_filter = [f for f in self.list_filter if f not in ('owner',)]
        return CustomReportAdmin.get_form_filter(self, request)

    def _calc_extra_from_qs(self, qs):
        workitem_keys = set()
        material_keys = set()
        id_extra_map = defaultdict(dict)
        for ticket in qs:
            tws = ticket.munka_halozat_jegy.all()
            workitem_keys |= set([tw.work_item for tw in tws])
            id_extra_map[ticket.pk].update(dict([(tw.work_item.art_number, tw.amount) for tw in tws]))
            price = sum([tw.work_item.art_price * tw.amount for tw in tws])
            if id_extra_map[ticket.pk]:
                id_extra_map[ticket.pk][u'Ár összesen'] = int(price)

            tms = ticket.anyag_halozat_jegy.all()
            material_keys |= set([tm.material for tm in tms])
            id_extra_map[ticket.pk].update(dict([(tm.material.sn, tm.amount) for tm in tms]))
            id_extra_map[ticket.pk][u'Szerelő'] = u', '.join([u.username for u in ticket.owner.all()])

        workitem_keys = sorted(list(workitem_keys), key=lambda x: x.art_number)
        material_keys = sorted(list(material_keys), key=lambda x: x.sn)
        wo_offsets = list(enumerate(workitem_keys + material_keys))
        self.calculated_columns = [(self.extra_columns_first_col, u'Szerelő')]
        self.calculated_columns.extend([(e[0]+self.extra_columns_first_col+1, e[1].art_number if hasattr(e[1], 'art_number') else e[1].sn) for e in wo_offsets])
        self.calculated_columns.append((len(self.calculated_columns + self.fields), u'Ár összesen'))
        self.extra_col_map = id_extra_map
        self.id_url_map = dict([(t.address, '/admin/rovidtav/networkticket/{}/change'.format(t.pk)) for t in qs])

    def get_render_context(self, request, extra_context={}, by_row=None):
        ctx = super(NetworkTicketSummaryList, self).get_render_context(
            request, extra_context, by_row)
        ctx['id_url_map'] = self.id_url_map
        return ctx


class NetworkElementWorkSummaryList(DedupedReportRows):

    title = u'Hálózati elem összesítő lista'
    model = NTNEWorkItem
    extra_columns_first_col = 6

    fields = [
        'network_element__address',
        'network_element__type__type_str',
        'network_element__ext_id',
        'network_element__ticket__onu',
        'created_at',
        'network_element__status',
    ]
    list_filter = ['network_element__ticket__onu',
                   'owner',
                   'created_at']
    list_filter_classes = {
        'network_element__ticket__onu': ChoiceField,
    }
    extra_col_map = {}
    override_field_formats = {
        'created_at': to_date,
        'network_element__status': to_status_str,
    }
    override_field_labels = {
        'network_element__city__onuk': Label(u'Onu'),
        'network_element__type__type_str': Label(u'Megnevezés'),
        'network_element__type__type': Label(u'Eszköz típus'),
        'network_element__city__name': Label(u'Település'),
    }

    def _short(self, name):
        return (name[:10] + '...') if len(name) > 13 else name

    def _calc_extra_from_qs(self, qs):
        ct = None
        sep = ' \r\n'
        ids = [obj.network_element.id for obj in qs]
        all_tws = NTNEWorkItem.objects.filter(network_element_id__in=ids)
        all_tms = NTNEMaterial.objects.filter(network_element_id__in=ids)
        workitem_keys = set()
        material_keys = set()
        id_extra_map = defaultdict(dict)
        for workitem in qs:
            ct = ct or workitem.network_element.get_content_type()
            tws = [tw for tw in all_tws if tw.network_element == workitem.network_element and
                   tw.owner == workitem.owner]
            notes = Note.objects.filter(content_type=ct, object_id=workitem.network_element.id)
            id_extra_map[workitem.pk][u'Megjegyzések'] = ' --- '.join([n.remark for n in notes])
            workitem_keys |= set([tw.work_item for tw in tws])
            for tw in tws:
                id_extra_map[workitem.pk].update(
                    {tw.work_item.art_number + sep + self._short(tw.work_item.name): str(tw.amount).replace(".", ",")})
                price = tw.work_item.art_price * tw.amount
                if id_extra_map[workitem.pk] and u'Ár összesen' in id_extra_map[workitem.pk]:
                    id_extra_map[workitem.pk][u'Ár összesen'] += int(price)
                else:
                    id_extra_map[workitem.pk][u'Ár összesen'] = int(price)
                    id_extra_map[workitem.pk][u'Szerelő'] = workitem.owner

            tms = [tm for tm in all_tms if tm.network_element == workitem.network_element and
                   tm.owner == workitem.owner]
            material_keys |= set([tm.material for tm in tms])
            for tm in tms:
                id_extra_map[workitem.pk].update(
                    {tm.material.sn + sep + self._short(tm.material.name): str(tm.amount).replace(".", ",")})

        workitem_keys = sorted(list(workitem_keys), key=lambda x: x.art_number + sep + self._short(x.name))
        material_keys = sorted(list(material_keys), key=lambda x: x.sn + sep + self._short(x.name))
        wo_offsets = list(enumerate(workitem_keys + material_keys))
        self.calculated_columns = [(self.extra_columns_first_col, u'Szerelő')]
        self.calculated_columns.extend(
            [(e[0]+self.extra_columns_first_col+1, e[1].art_number + sep + self._short(e[1].name)
              if hasattr(e[1], 'art_number') else e[1].sn + sep + self._short(e[1].name))
             for e in wo_offsets])
        self.calculated_columns.append(
            (len(self.calculated_columns + self.fields), u'Ár összesen'))
        self.calculated_columns.append(
            (len(self.calculated_columns + self.fields), u'Megjegyzések'))
        self.extra_col_map = id_extra_map
        self.id_url_map = dict(
            [(t.network_element.address,
              '/admin/rovidtav/networkticketnetworkelement/{}/change'.format(t.pk))
             for t in qs])


class HistoryReport(CustomReportAdmin):

    title = u'Jegy történet riport'
    model = Note
    fields = [
        'remark',
        'created_at',
    ]

    list_filter = ['created_at', 'created_by']
    list_order_by = ('-created_at',)
    type = 'report'
    override_field_formats = {
        'created_at': to_date,
    }
    extra_col_map = {}

    def get_query_set(self, filter_kwargs):
        qs = CustomReportAdmin.get_query_set(self, filter_kwargs)
        return qs.filter(is_history=True)


class IndividualWIReport(CustomReportAdmin):

    title = u'Egyedi munka riport'
    model = IndividualWorkItem
    fields = [
        'owner__username',
        'work_date',
        'price',
        'remark',
    ]
    override_field_labels = {
        'owner__username': Label(u'Dolgozó'),
        'work_date': Label(u'Dátum'),
    }
    list_filter = ['work_date', 'owner']
    list_order_by = ('-work_date',)
    type = 'report'
    override_field_formats = {
        'work_date': to_date,
    }
    extra_col_map = {}


reports.register('osszesito', SummaryList)
reports.register('riport_cimkek_alapjan', OnDemandList)
reports.register('halozati_riport_cimkek_alapjan', OnDemandNetworkTicketList)
reports.register('halozati_jegy_osszesito', NetworkTicketSummaryList)
reports.register('halozati_elem_osszesito', NetworkElementWorkSummaryList)
reports.register('tortenet', HistoryReport)
reports.register('egyedi_munka_riport', IndividualWIReport)
