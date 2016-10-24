# -*- coding: utf-8 -*-

import os
import re
import base64

from unidecode import unidecode
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey


class Const(object):

    NO_OWNER = u'Nincs'

    MIND = 0
    REZ = 1
    KOAX = 2
    OPTIKA = 3
    SAT = 4

    EXT_MAP = {
        '.htm': 'text/html',
        '.html': 'text/html',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.pdf': 'application/pdf',
    }


class BaseEntity(models.Model):
    class Meta:
        abstract = True

    def get_content_type_obj(self):
        return ContentType.objects.get_for_model(self)

    def get_content_type(self):
        return ContentType.objects.get_for_model(self).id

    def get_content_type_name(self):
        return ContentType.objects.get_for_model(self).name


class ApplicantAttributes(BaseEntity):

    user = models.OneToOneField(User)
    percent = models.IntegerField(db_column='szazalek',
                                  verbose_name=u'Százelék')

    class Meta:
        db_table = 'alkalmazott_tul'
        verbose_name = u'Alkalmazott tul.'
        verbose_name_plural = u'Alkalmazott tul.'

    def __unicode__(self):
        return u'{}'.format(self.user)


class City(BaseEntity):

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

    @staticmethod
    def autocomplete_search_fields():
        return ('name', 'zip')


class Client(BaseEntity):

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

    @staticmethod
    def autocomplete_search_fields():
        return ('name', 'mt_id')


class DeviceType(BaseEntity):

    name = models.CharField(db_column='nev', max_length=50,
                            verbose_name=u'Típus')
    sn_pattern = models.CharField(db_column='vonalkod_minta', max_length=50,
                                  null=True, blank=True,
                                  verbose_name=u'Vonalkód minta')
    technology = models.IntegerField(
        db_column='technologia',
        choices=(
            (Const.MIND, u'Mind'),
            (Const.REZ, u'Réz'),
            (Const.OPTIKA, u'Optika'),
            (Const.KOAX, u'Koax'),
            (Const.SAT, u'SAT'),
        ),
        default=0,
        verbose_name=u'Technológia',
    )

    class Meta:
        db_table = 'eszkoz_tipus'
        verbose_name = u'Eszköz típus'
        verbose_name_plural = u'Eszköz típusok'

    def __unicode__(self):
        return self.name

    @staticmethod
    def autocomplete_search_fields():
        return ('name',)


class Device(BaseEntity):

    sn = models.CharField(db_column='vonalkod', max_length=50,
                          verbose_name=u'Vonalkód')
    type = models.ForeignKey(DeviceType, db_column='tipus',
                             verbose_name=u'Típus')
    card_sn = models.CharField(db_column='kartya', max_length=50,
                               verbose_name=u'Kártya',
                               null=True, blank=True)

    class Meta:
        db_table = 'eszkoz'
        verbose_name = u'Eszköz'
        verbose_name_plural = u'Eszközök'

    def __unicode__(self):
        return u'{} - {}'.format(self.sn, self.type)

    @staticmethod
    def autocomplete_search_fields():
        return ('sn',)

    @property
    def owner(self):
        try:
            return DeviceOwner.objects.get(device=self)
        except DeviceOwner.DoesNotExist:
            return None


class DeviceOwner(BaseEntity):

    device = models.ForeignKey(Device, db_column='eszkoz',
                               verbose_name=u'Eszköz')

    content_type = models.ForeignKey(ContentType, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    owner = GenericForeignKey()

    class Meta:
        db_table = 'eszkoz_tulajdon'
        verbose_name = u'Eszköz tulajdonos'
        verbose_name_plural = u'Eszköz tulajdonosok'

    def save(self, *args, **kwargs):
        if self.pk:
            prev = DeviceOwner.objects.get(pk=self.pk)
            if self.owner != prev.owner:
                prev_owner = Const.NO_OWNER if not prev.owner else \
                    prev.name
                owner = Const.NO_OWNER if not self.owner else \
                    self.name
                remark = u'Új tulajdonos: {} >> {}'.format(prev_owner, owner)
                Note.objects.create(
                    content_type=self.device.get_content_type_obj(),
                    object_id=self.device.pk,
                    remark=remark, is_history=True)

        return super(DeviceOwner, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name

    @property
    def name(self):
        if hasattr(self.owner, 'username'):
            return self.owner.username
        return unicode(self.owner)


class Payoff(BaseEntity):

    name = models.CharField(db_column='nev', max_length=70,
                            verbose_name=u'Név')

    class Meta:
        db_table = 'elszamolas'
        verbose_name = u'Elszámolás'
        verbose_name_plural = u'Elszámolások'

    def __unicode__(self):
        return unicode(self.name)

    @staticmethod
    def autocomplete_search_fields():
        return ('name',)


class TicketType(BaseEntity):

    name = models.CharField(db_column='nev', max_length=250,
                            verbose_name=u'Név')
    remark = models.TextField(db_column='megjegyzes',
                              verbose_name=u'Megjegyzés',
                              null=True, blank=True)

    class Meta:
        db_table = 'jegy_tipus'
        verbose_name = u'Jegy típus'
        verbose_name_plural = u'Jegy típusok'

    def __unicode__(self):
        return unicode(self.name)

    @staticmethod
    def autocomplete_search_fields():
        return ('name',)


class Ticket(BaseEntity):

    ext_id = models.CharField(db_column='kulso_id', max_length=20,
                              verbose_name=u'Jegy ID')
    client = models.ForeignKey(Client, db_column='ugyfel',
                               verbose_name=u'Ügyfél')
    ticket_types = models.ManyToManyField(TicketType, db_column='tipus',
                                          verbose_name=u'Jegy típus')
    city = models.ForeignKey(City, db_column='telepules',
                             verbose_name=u'Település')
    address = models.CharField(db_column='cim', max_length=120,
                               verbose_name=u'Cím')
    payoff = models.ForeignKey(Payoff, db_column='elszamolas',
                               null=True, blank=True,
                               verbose_name=u'Elszámolás')
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

    created_at = models.DateTimeField(verbose_name=u'Létrehozva')
    created_by = models.ForeignKey(User, editable=False,
                                   verbose_name=u'Létrehozó')

    class Meta:
        db_table = 'jegy'
        verbose_name = u'Jegy'
        verbose_name_plural = u'Jegyek'

    @staticmethod
    def autocomplete_search_fields():
        return ('ext_id', 'address')

    def devices(self):
        return Device.objects.get(client=self.client)

    def technology(self):
        if not hasattr(self, '_technology'):
            self._technology = Const.MIND
            technology_map = {
                'rez': Const.REZ,
                'adsl': Const.REZ,
                'mdf': Const.REZ,
                'optika': Const.OPTIKA,
                'gpon': Const.OPTIKA,
                'koax': Const.KOAX,
                'sat': Const.SAT,
                'dvbs': Const.SAT,
            }
            tts = [tt.name for tt in self.ticket_types.all()]
            full_type = unidecode(' '.join(tts)).lower()
            for match, tech in technology_map.iteritems():
                if match in full_type:
                    self._technology = tech
                    break
        return self._technology

    def __unicode__(self):
        ttype = u' '.join(t.name for t in self.ticket_types.all())
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
        self._trans(u'Státusz változás', old_status, new_status)

    def _owner_trans(self, prev_inst):
        """
        Creates the ticketevent for an owner change and returns the owners
        """
        prev_owner = Const.NO_OWNER if not prev_inst.owner else \
            prev_inst.owner.username
        owner = Const.NO_OWNER if not self.owner else self.owner.username
        self._trans(u'Új tulajdonos', prev_owner, owner)

    def _trans(self, event, old, new):
        """
        Creates the ticketevent object for a change
        """
        remark = u'{}: '.format(event) if event else u''
        remark += u'{} >> {}'.format(old, new)
        Note.objects.create(content_object=self,
                            remark=remark, is_history=True)


class Note(BaseEntity):

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()
    # Tells if the instance has been auto generated or manually added
    is_history = models.BooleanField(default=False)
    remark = models.TextField(db_column='megjegyzes',
                              verbose_name=u'Megjegyzés')

    created_at = models.DateTimeField(auto_now_add=True, editable=False,
                                      verbose_name=u'Létrehozva')
    created_by = models.ForeignKey(User, editable=False,
                                   verbose_name=u'Létrehozó')

    class Meta:
        db_table = 'megjegyzes'
        verbose_name = u'Megjegyzés'
        verbose_name_plural = u'Megjegyzések'

    def __unicode__(self):
        return self.remark[:25]


class MaterialCategory(BaseEntity):

    name = models.CharField(db_column='nev', max_length=70,
                            verbose_name=u'Kategória név')
    remark = models.TextField(db_column='megjegyzes',
                              null=True, blank=True,
                              verbose_name=u'Megjegyzés')

    class Meta:
        db_table = 'anyag_kategoria'
        verbose_name = u'Anyag Kategória'
        verbose_name_plural = u'Anyag Kategóriák'

    def __unicode__(self):
        return self.name

    @staticmethod
    def autocomplete_search_fields():
        return ('name',)


class Material(BaseEntity):

    sn = models.CharField(db_column='cikkszam', max_length=40,
                          verbose_name=u'Cikkszám')
    name = models.CharField(db_column='nev', max_length=70,
                            verbose_name=u'Név')
    category = models.ForeignKey(MaterialCategory, db_column='kategoria',
                                 verbose_name=u'Kategória')
    price = models.IntegerField(db_column='iranyar', verbose_name=u'Irányár',
                                default=0)
    fav = models.BooleanField(db_column='kedvenc', verbose_name=u'Kedvenc',
                              default=False)
    unit = models.CharField(
        db_column='egyseg',
        choices=(
            ('db', u'db'),
            ('m', u'm'),
            ('km', u'km'),
            ('klt', u'klt'),
            ('csom', u'csom'),
            ('kg', u'kg'),
        ),
        max_length=50,
        verbose_name=u'Egység',
    )
    remark = models.TextField(db_column='megjegyzes',
                              null=True, blank=True,
                              verbose_name=u'Megjegyzés')
    comes_from = models.CharField(
        db_column='biztositja',
        choices=(
            # ('BI', u'BI-től veszi'),
            ('MT', u'MT Biztosítja'),
            ('R', u'Váll. rezsi'),
        ),
        max_length=50,
        null=True, blank=True,
        verbose_name=u'Biztosítja',
    )
    technology = models.IntegerField(
        db_column='technologia',
        choices=(
            (Const.MIND, u'Mind'),
            (Const.REZ, u'Réz'),
            (Const.OPTIKA, u'Optika'),
            (Const.KOAX, u'Koax'),
            (Const.SAT, u'SAT'),
        ),
        default=0,
        verbose_name=u'Technológia',
    )

    class Meta:
        db_table = 'anyag'
        verbose_name = u'Anyag'
        verbose_name_plural = u'Anyagok'

    def __unicode__(self):
        return self.name

    @staticmethod
    def autocomplete_search_fields():
        return ('name', 'sn')


class TicketMaterial(BaseEntity):

    ticket = models.ForeignKey(Ticket, db_column='jegy',
                               related_name='anyag_jegy',
                               verbose_name=u'Jegy')
    material = models.ForeignKey(Material, db_column='anyag',
                                 verbose_name=u'Anyag')
    amount = models.FloatField(db_column='mennyiseg',
                               verbose_name=u'Mennyiség',
                               default=1)

    created_at = models.DateTimeField(auto_now_add=True, editable=False,
                                      verbose_name=u'Létrehozva')
    created_by = models.ForeignKey(User, editable=False,
                                   verbose_name=u'Létrehozó')

    class Meta:
        db_table = 'anyag_jegy'
        verbose_name = u'Jegy Anyag'
        verbose_name_plural = u'Jegy Anyagok'

    def __unicode__(self):
        return u'{} - {}'.format(unicode(self.ticket),
                                 unicode(self.material))


class WorkItem(BaseEntity):

    name = models.CharField(db_column='nev', max_length=300,
                            verbose_name=u'Név')
    art_number = models.CharField(db_column='tetelszam', max_length=40,
                                  verbose_name=u'Tételszám', default=0)
    remark = models.TextField(db_column='definicio',
                              null=True, blank=True,
                              verbose_name=u'Definíció')
    art_price = models.IntegerField(db_column='tetel_ar',
                                    verbose_name=u'Tétel ár', default=0)
    bulk_price = models.IntegerField(db_column='csop_anyag_ar', default=0,
                                     verbose_name=u'Csoportos anyag ár')
    given_price = models.IntegerField(db_column='kiadott_ar',
                                      verbose_name=u'Kiadott ár', default=0)

    class Meta:
        db_table = 'munka'
        verbose_name = u'Munkatétel'
        verbose_name_plural = u'Munkatételek'

    def __unicode__(self):
        return self.name

    @staticmethod
    def autocomplete_search_fields():
        return ('name', 'art_number')


class TicketWorkItem(BaseEntity):

    ticket = models.ForeignKey(Ticket, db_column='jegy',
                               verbose_name=u'Jegy')
    work_item = models.ForeignKey(WorkItem, db_column='munka',
                                  verbose_name=u'Munka')

    created_at = models.DateTimeField(auto_now_add=True, editable=False,
                                      verbose_name=u'Létrehozva')
    created_by = models.ForeignKey(User, editable=False,
                                   verbose_name=u'Létrehozó')

    class Meta:
        db_table = 'munka_jegy'
        verbose_name = u'Munka'
        verbose_name_plural = u'Munkák'

    def __unicode__(self):
        return u'{} - {}'.format(unicode(self.ticket),
                                 unicode(self.work_item))


class Attachment(BaseEntity):

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

    @staticmethod
    def autocomplete_search_fields():
        return ('name',)

    @property
    def data(self):
        return base64.b64decode(self._data)

    @property
    def content_type(self):
        _, ext = os.path.splitext(self.name)
        return Const.EXT_MAP.get(ext.lower(), 'text/html')

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Check if the data is already encoded b64
        r = re.compile(r'(?:[A-Za-z0-9+/]{4}){2,}(?:[A-Za-z0-9+/]{2}'
                       r'[AEIMQUYcgkosw048]=|[A-Za-z0-9+/][AQgw]==)')
        if not r.match(self._data):
            self._data = base64.b64encode(self._data)

        super(Attachment, self).save(*args, **kwargs)
