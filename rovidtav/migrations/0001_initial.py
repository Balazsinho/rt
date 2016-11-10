# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-10-24 10:03
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ApplicantAttributes',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('percent', models.IntegerField(db_column=b'szazalek', verbose_name='Sz\xe1zel\xe9k')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'alkalmazott_tul',
                'verbose_name': 'Alkalmazott tul.',
                'verbose_name_plural': 'Alkalmazott tul.',
            },
        ),
        migrations.CreateModel(
            name='Attachment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, db_column=b'nev', max_length=120, null=True, verbose_name='N\xe9v')),
                ('_data', models.TextField(db_column=b'adat', verbose_name='Adat')),
                ('remark', models.TextField(blank=True, db_column=b'megjegyzes', null=True, verbose_name='Megjegyz\xe9s')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='L\xe9trehozva')),
                ('created_by', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='L\xe9trehoz\xf3')),
            ],
            options={
                'db_table': 'csatolmany',
                'verbose_name': 'File',
                'verbose_name_plural': 'Fileok',
            },
        ),
        migrations.CreateModel(
            name='City',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_column=b'nev', max_length=60, verbose_name='N\xe9v')),
                ('zip', models.IntegerField(db_column=b'irsz', verbose_name='Irsz')),
                ('primer', models.CharField(blank=True, db_column=b'primer', max_length=60, null=True, verbose_name='Primer')),
                ('onuk', models.CharField(blank=True, db_column=b'onuk', max_length=200, null=True, verbose_name='Onuk')),
            ],
            options={
                'db_table': 'telepules',
                'verbose_name': 'Telep\xfcl\xe9s',
                'verbose_name_plural': 'Telep\xfcl\xe9sek',
            },
        ),
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mt_id', models.CharField(db_column=b'mt_id', max_length=20)),
                ('name', models.CharField(db_column=b'nev', max_length=70, verbose_name='N\xe9v')),
                ('address', models.CharField(db_column=b'cim', max_length=120, verbose_name='C\xedm')),
                ('phone', models.CharField(db_column=b'telefon', max_length=300, verbose_name='Telefon')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_column=b'letrehozas_datum', verbose_name='L\xe9trehozva')),
                ('city', models.ForeignKey(db_column=b'telepules', on_delete=django.db.models.deletion.CASCADE, to='rovidtav.City', verbose_name='Telep\xfcl\xe9s')),
                ('created_by', models.ForeignKey(db_column=b'letrehozas_fh', editable=False, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='L\xe9trehoz\xf3')),
            ],
            options={
                'db_table': 'ugyfel',
                'verbose_name': '\xdcgyf\xe9l',
                'verbose_name_plural': '\xdcgyfelek',
            },
        ),
        migrations.CreateModel(
            name='Device',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sn', models.CharField(db_column=b'vonalkod', max_length=50, verbose_name='Vonalk\xf3d')),
                ('card_sn', models.CharField(blank=True, db_column=b'kartya', max_length=50, null=True, verbose_name='K\xe1rtya')),
            ],
            options={
                'db_table': 'eszkoz',
                'verbose_name': 'Eszk\xf6z',
                'verbose_name_plural': 'Eszk\xf6z\xf6k',
            },
        ),
        migrations.CreateModel(
            name='DeviceOwner',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('content_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
                ('device', models.ForeignKey(db_column=b'eszkoz', on_delete=django.db.models.deletion.CASCADE, to='rovidtav.Device', verbose_name='Eszk\xf6z')),
            ],
            options={
                'db_table': 'eszkoz_tulajdon',
                'verbose_name': 'Eszk\xf6z tulajdonos',
                'verbose_name_plural': 'Eszk\xf6z tulajdonosok',
            },
        ),
        migrations.CreateModel(
            name='DeviceType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_column=b'nev', max_length=50, verbose_name='T\xedpus')),
                ('sn_pattern', models.CharField(blank=True, db_column=b'vonalkod_minta', max_length=50, null=True, verbose_name='Vonalk\xf3d minta')),
                ('technology', models.IntegerField(choices=[(0, 'Mind'), (1, 'R\xe9z'), (3, 'Optika'), (2, 'Koax'), (4, 'SAT')], db_column=b'technologia', default=0, verbose_name='Technol\xf3gia')),
            ],
            options={
                'db_table': 'eszkoz_tipus',
                'verbose_name': 'Eszk\xf6z t\xedpus',
                'verbose_name_plural': 'Eszk\xf6z t\xedpusok',
            },
        ),
        migrations.CreateModel(
            name='Material',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sn', models.CharField(db_column=b'cikkszam', max_length=40, verbose_name='Cikksz\xe1m')),
                ('name', models.CharField(db_column=b'nev', max_length=70, verbose_name='N\xe9v')),
                ('price', models.IntegerField(db_column=b'iranyar', default=0, verbose_name='Ir\xe1ny\xe1r')),
                ('fav', models.BooleanField(db_column=b'kedvenc', default=False, verbose_name='Kedvenc')),
                ('unit', models.CharField(choices=[(b'db', 'db'), (b'm', 'm'), (b'km', 'km'), (b'klt', 'klt'), (b'csom', 'csom'), (b'kg', 'kg')], db_column=b'egyseg', max_length=50, verbose_name='Egys\xe9g')),
                ('remark', models.TextField(blank=True, db_column=b'megjegyzes', null=True, verbose_name='Megjegyz\xe9s')),
                ('comes_from', models.CharField(blank=True, choices=[(b'MT', 'MT Biztos\xedtja'), (b'R', 'V\xe1ll. rezsi')], db_column=b'biztositja', max_length=50, null=True, verbose_name='Biztos\xedtja')),
                ('technology', models.IntegerField(choices=[(0, 'Mind'), (1, 'R\xe9z'), (3, 'Optika'), (2, 'Koax'), (4, 'SAT')], db_column=b'technologia', default=0, verbose_name='Technol\xf3gia')),
            ],
            options={
                'db_table': 'anyag',
                'verbose_name': 'Anyag',
                'verbose_name_plural': 'Anyagok',
            },
        ),
        migrations.CreateModel(
            name='MaterialCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_column=b'nev', max_length=70, verbose_name='Kateg\xf3ria n\xe9v')),
                ('remark', models.TextField(blank=True, db_column=b'megjegyzes', null=True, verbose_name='Megjegyz\xe9s')),
            ],
            options={
                'db_table': 'anyag_kategoria',
                'verbose_name': 'Anyag Kateg\xf3ria',
                'verbose_name_plural': 'Anyag Kateg\xf3ri\xe1k',
            },
        ),
        migrations.CreateModel(
            name='Note',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField()),
                ('is_history', models.BooleanField(default=False)),
                ('remark', models.TextField(db_column=b'megjegyzes', verbose_name='Megjegyz\xe9s')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='L\xe9trehozva')),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
                ('created_by', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='L\xe9trehoz\xf3')),
            ],
            options={
                'db_table': 'megjegyzes',
                'verbose_name': 'Megjegyz\xe9s',
                'verbose_name_plural': 'Megjegyz\xe9sek',
            },
        ),
        migrations.CreateModel(
            name='Payoff',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_column=b'nev', max_length=70, verbose_name='N\xe9v')),
            ],
            options={
                'db_table': 'elszamolas',
                'verbose_name': 'Elsz\xe1mol\xe1s',
                'verbose_name_plural': 'Elsz\xe1mol\xe1sok',
            },
        ),
        migrations.CreateModel(
            name='Ticket',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ext_id', models.CharField(db_column=b'kulso_id', max_length=20, verbose_name='Jegy ID')),
                ('address', models.CharField(db_column=b'cim', max_length=120, verbose_name='C\xedm')),
                ('status', models.CharField(choices=[('\xdaj', '\xdaj'), ('Kiadva', 'Kiadva'), ('Folyamatban', 'Folyamatban'), ('Lez\xe1rva', 'Lez\xe1rva'), ('Duplik\xe1lt', 'Duplik\xe1lt')], db_column=b'statusz', default='\xdaj', max_length=100, verbose_name='St\xe1tusz')),
                ('additional', models.TextField(blank=True, null=True, verbose_name='Egy\xe9b')),
                ('created_at', models.DateTimeField(verbose_name='L\xe9trehozva')),
                ('city', models.ForeignKey(db_column=b'telepules', on_delete=django.db.models.deletion.CASCADE, to='rovidtav.City', verbose_name='Telep\xfcl\xe9s')),
                ('client', models.ForeignKey(db_column=b'ugyfel', on_delete=django.db.models.deletion.CASCADE, to='rovidtav.Client', verbose_name='\xdcgyf\xe9l')),
                ('created_by', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='L\xe9trehoz\xf3')),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tulajdonos', to=settings.AUTH_USER_MODEL, verbose_name='Tulajdonos')),
                ('payoff', models.ForeignKey(blank=True, db_column=b'elszamolas', null=True, on_delete=django.db.models.deletion.CASCADE, to='rovidtav.Payoff', verbose_name='Elsz\xe1mol\xe1s')),
            ],
            options={
                'db_table': 'jegy',
                'verbose_name': 'Jegy',
                'verbose_name_plural': 'Jegyek',
            },
        ),
        migrations.CreateModel(
            name='TicketMaterial',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.FloatField(db_column=b'mennyiseg', default=1, verbose_name='Mennyis\xe9g')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='L\xe9trehozva')),
                ('created_by', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='L\xe9trehoz\xf3')),
                ('material', models.ForeignKey(db_column=b'anyag', on_delete=django.db.models.deletion.CASCADE, to='rovidtav.Material', verbose_name='Anyag')),
                ('ticket', models.ForeignKey(db_column=b'jegy', on_delete=django.db.models.deletion.CASCADE, related_name='anyag_jegy', to='rovidtav.Ticket', verbose_name='Jegy')),
            ],
            options={
                'db_table': 'anyag_jegy',
                'verbose_name': 'Jegy Anyag',
                'verbose_name_plural': 'Jegy Anyagok',
            },
        ),
        migrations.CreateModel(
            name='TicketType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_column=b'nev', max_length=250, verbose_name='N\xe9v')),
                ('remark', models.TextField(blank=True, db_column=b'megjegyzes', null=True, verbose_name='Megjegyz\xe9s')),
            ],
            options={
                'db_table': 'jegy_tipus',
                'verbose_name': 'Jegy t\xedpus',
                'verbose_name_plural': 'Jegy t\xedpusok',
            },
        ),
        migrations.CreateModel(
            name='TicketWorkItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='L\xe9trehozva')),
                ('created_by', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='L\xe9trehoz\xf3')),
                ('ticket', models.ForeignKey(db_column=b'jegy', on_delete=django.db.models.deletion.CASCADE, to='rovidtav.Ticket', verbose_name='Jegy')),
            ],
            options={
                'db_table': 'munka_jegy',
                'verbose_name': 'Munka',
                'verbose_name_plural': 'Munk\xe1k',
            },
        ),
        migrations.CreateModel(
            name='WorkItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_column=b'nev', max_length=300, verbose_name='N\xe9v')),
                ('art_number', models.CharField(db_column=b'tetelszam', default=0, max_length=40, verbose_name='T\xe9telsz\xe1m')),
                ('remark', models.TextField(blank=True, db_column=b'definicio', null=True, verbose_name='Defin\xedci\xf3')),
                ('art_price', models.IntegerField(db_column=b'tetel_ar', default=0, verbose_name='T\xe9tel \xe1r')),
                ('bulk_price', models.IntegerField(db_column=b'csop_anyag_ar', default=0, verbose_name='Csoportos anyag \xe1r')),
                ('given_price', models.IntegerField(db_column=b'kiadott_ar', default=0, verbose_name='Kiadott \xe1r')),
            ],
            options={
                'db_table': 'munka',
                'verbose_name': 'Munkat\xe9tel',
                'verbose_name_plural': 'Munkat\xe9telek',
            },
        ),
        migrations.AddField(
            model_name='ticketworkitem',
            name='work_item',
            field=models.ForeignKey(db_column=b'munka', on_delete=django.db.models.deletion.CASCADE, to='rovidtav.WorkItem', verbose_name='Munka'),
        ),
        migrations.AddField(
            model_name='ticket',
            name='ticket_types',
            field=models.ManyToManyField(db_column=b'tipus', to='rovidtav.TicketType', verbose_name='Jegy t\xedpus'),
        ),
        migrations.AddField(
            model_name='material',
            name='category',
            field=models.ForeignKey(db_column=b'kategoria', on_delete=django.db.models.deletion.CASCADE, to='rovidtav.MaterialCategory', verbose_name='Kateg\xf3ria'),
        ),
        migrations.AddField(
            model_name='device',
            name='type',
            field=models.ForeignKey(db_column=b'tipus', on_delete=django.db.models.deletion.CASCADE, to='rovidtav.DeviceType', verbose_name='T\xedpus'),
        ),
        migrations.AddField(
            model_name='attachment',
            name='ticket',
            field=models.ForeignKey(db_column=b'jegy', on_delete=django.db.models.deletion.CASCADE, to='rovidtav.Ticket', verbose_name='Jegy'),
        ),
    ]
