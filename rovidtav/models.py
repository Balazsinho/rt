# -*- coding: utf-8 -*-

import os
import re
import base64

from django.db import models
from django.contrib.auth.models import User


class City(models.Model):

    name = models.CharField(db_column='nev', max_length=60,
                            verbose_name=u'Név')
    zip = models.IntegerField(db_column='irsz', verbose_name=u'Irsz')
    primer = models.CharField(db_column='primer', max_length=60,
                              verbose_name=u'Primer',
                              null=True, blank=True)
    onuk = models.CharField(db_column='onuk', max_length=200,
                            verbose_name=u'Onuk',
                            null=True, blank=True)

    class Meta:
        db_table = 'telepules'
        verbose_name = u'Település'
        verbose_name_plural = u'Települések'

    def __unicode__(self):
        return u'{} ({})'.format(self.name, self.zip)


class Client(models.Model):

    mt_id = models.CharField(db_column='mt_id', max_length=20)
    name = models.CharField(db_column='nev', max_length=70,
                            verbose_name=u'Név')
    city = models.ForeignKey(City, db_column='telepules',
                             verbose_name=u'Település')
    address = models.CharField(db_column='cim', max_length=120,
                               verbose_name=u'Cím')
    phone = models.CharField(db_column='telefon', max_length=300,
                             verbose_name=u'Telefon')

    created_at = models.DateTimeField(db_column='letrehozas_datum',
                                      auto_now_add=True,
                                      verbose_name=u'Létrehozva')
    created_by = models.ForeignKey(User, db_column='letrehozas_fh',
                                   editable=False,
                                   verbose_name=u'Létrehozó')

    class Meta:
        db_table = 'ugyfel'
        verbose_name = u'Ügyfél'
        verbose_name_plural = u'Ügyfelek'

    def __unicode__(self):
        return u'{} ({})'.format(self.name, self.mt_id)


class DeviceType(models.Model):

    name = models.CharField(db_column='nev', max_length=50,
                            verbose_name=u'Név')
    remark = models.TextField(db_column='megjegyzes',
                              verbose_name=u'Megjegyzés')

    class Meta:
        db_table = 'eszkoz_tipus'
        verbose_name = u'Eszköz típus'
        verbose_name_plural = u'Eszköz típusok'

    def __unicode__(self):
        return self.name


class Device(models.Model):

    sn = models.CharField(db_column='vonalkod', max_length=30,
                          verbose_name=u'Vonalkód')
    type = models.ForeignKey(DeviceType, db_column='tipus',
                             verbose_name=u'Típus')
    connected_device = models.ForeignKey('Device', db_column='kapcs_eszkoz',
                                         verbose_name=u'Kapcsolódó eszköz',
                                         null=True, blank=True)
    show = models.BooleanField(db_column='valid', default=True,
                               verbose_name=u'Érvényes')
    remark = models.TextField(db_column='megjegyzes',
                              verbose_name=u'Megjegyzés',
                              null=True, blank=True)

    class Meta:
        db_table = 'eszkoz'
        verbose_name = u'Eszköz'
        verbose_name_plural = u'Eszközök'

    def __unicode__(self):
        return self.sn


class TicketType(models.Model):

    name = models.CharField(db_column='nev', max_length=70,
                            verbose_name=u'Név')

    class Meta:
        db_table = 'jegy_tipus'
        verbose_name = u'Jegy típus'
        verbose_name_plural = u'Jegy típusok'

    def __unicode__(self):
        return unicode(self.name)


class Ticket(models.Model):

    NO_OWNER = u'Nincs'

    ext_id = models.CharField(db_column='kulso_id', max_length=20,
                              verbose_name=u'Jegy azonosító')
    client = models.ForeignKey(Client, db_column='ugyfel',
                               verbose_name=u'Ügyfél')
    ticket_type = models.ForeignKey(TicketType, db_column='tipus',
                                    verbose_name=u'Jegy típus')
    city = models.ForeignKey(City, db_column='telepules',
                             verbose_name=u'Település')
    address = models.CharField(db_column='cim', max_length=120,
                               verbose_name=u'Cím')

    owner = models.ForeignKey(User, related_name='tulajdonos',
                              null=True, blank=True,
                              verbose_name=u'Tulajdonos')
    status = models.CharField(
        db_column='statusz',
        null=False,
        blank=False,
        default=u'Új',
        choices=(
            (u'Új', u'Új'),
            (u'Kiadva', u'Kiadva'),
            (u'Folyamatban', u'Folyamatban'),
            (u'Lezárva', u'Lezárva'),
            (u'Duplikált', u'Duplikált'),
        ),
        max_length=100,
        verbose_name=u'Státusz',
    )

    additional = models.TextField(null=True, blank=True,
                                  verbose_name=u'Egyéb')

    created_at = models.DateTimeField(auto_now_add=True, editable=False,
                                      verbose_name=u'Létrehozva')
    created_by = models.ForeignKey(User, editable=False,
                                   verbose_name=u'Létrehozó')

    class Meta:
        db_table = 'jegy'
        verbose_name = u'Jegy'
        verbose_name_plural = u'Jegyek'

    def __unicode__(self):
        ttype = unicode(self.ticket_type)
        ttype = ttype[:25] + u'...' if len(ttype) > 25 else ttype
        return unicode(u'{} - {}'.format(self.client, ttype))

    def save(self, *args, **kwargs):
        if self.pk:
            prev_inst = Ticket.objects.get(pk=self.pk)
            if self.owner != prev_inst.owner:
                self._owner_trans(prev_inst)

                if self.status == u'Új' and self.owner:
                    self.status = u'Kiadva'

                elif self.status != u'Új' and not self.owner:
                    self.status = u'Új'

            if self.status != prev_inst.status:
                self._status_trans(prev_inst.status, self.status)

        super(Ticket, self).save(*args, **kwargs)

    def _status_trans(self, old_status, new_status):
        """
        Does a status transition from old to new
        """
        self._trans(old_status, new_status, 'StatValt')

    def _owner_trans(self, prev_inst):
        """
        Creates the ticketevent for an owner change and returns the owners
        """
        prev_owner = self.NO_OWNER if not prev_inst.owner else \
            prev_inst.owner.username
        owner = self.NO_OWNER if not self.owner else self.owner.username
        self._trans(prev_owner, owner, 'TulValt')

    def _trans(self, old, new, event):
        """
        Creates the ticketevent object for a change
        """
        remark = u'{} -> {}'.format(old, new)
        TicketEvent.objects.create(ticket=self, event=event,
                                   remark=remark)


class TicketEvent(models.Model):

    ticket = models.ForeignKey(Ticket, db_column='jegy',
                               verbose_name=u'Jegy')
    event = models.CharField(
        db_column='esemeny',
        choices=(
            ('Megj', u'Megjegyzés'),
            ('TulValt', u'Tulajdonos változtatás'),
            ('StatValt', u'Státusz változtatás'),
            ('Doku', u'Dokumentum feltöltés'),
        ),
        max_length=100,
        verbose_name=u'Típus',
    )
    remark = models.TextField(db_column='megjegyzes',
                              verbose_name=u'Megjegyzés')

    created_at = models.DateTimeField(auto_now_add=True, editable=False,
                                      verbose_name=u'Létrehozva')
    created_by = models.ForeignKey(User, editable=False,
                                   verbose_name=u'Létrehozó')

    class Meta:
        db_table = 'jegy_esemeny'
        verbose_name = u'Esemény'
        verbose_name_plural = u'Megjegyzések'

    def __unicode__(self):
        return self.event


class Attachment(models.Model):

    EXT_MAP = {
        '.htm': 'text/html',
        '.html': 'text/html',
        '.jpg': 'image/jpeg',
        '.png': 'image/png',
        '.pdf': 'application/pdf',
    }

    ticket = models.ForeignKey(Ticket, db_column='jegy',
                               verbose_name=u'Jegy')
    name = models.CharField(db_column='nev', max_length=120,
                            verbose_name=u'Név',
                            null=True, blank=True)
    _data = models.TextField(db_column='adat',
                             verbose_name=u'Adat')
    remark = models.TextField(db_column='megjegyzes',
                              verbose_name=u'Megjegyzés',
                              null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, editable=False,
                                      verbose_name=u'Létrehozva')
    created_by = models.ForeignKey(User, editable=False,
                                   verbose_name=u'Létrehozó')

    class Meta:
        db_table = 'csatolmany'
        verbose_name = u'File'
        verbose_name_plural = u'Fileok'

    @property
    def data(self):
        return base64.b64decode(self._data)

    @property
    def content_type(self):
        _, ext = os.path.splitext(self.name)
        return self.EXT_MAP.get(ext, 'text/html')

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Check if the data is already encoded b64
        r = re.compile(r'(?:[A-Za-z0-9+/]{4}){2,}(?:[A-Za-z0-9+/]{2}'
                       r'[AEIMQUYcgkosw048]=|[A-Za-z0-9+/][AQgw]==)')
        if not r.match(self._data):
            self._data = base64.b64encode(self._data)

        super(Attachment, self).save(*args, **kwargs)
