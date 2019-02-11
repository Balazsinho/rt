# -*- coding: utf-8 -*-

from django.contrib.auth.models import User
from django.contrib.admin.filters import SimpleListFilter
from rovidtav.admin_helpers import get_technician_choices,\
    get_network_technician_choices, get_unintall_technician_choices
from rovidtav.models import Payoff


class OwnerFilter(SimpleListFilter):

    title = u'Szerelő'
    parameter_name = 'owner'

    def lookups(self, request, model_admin):
        return get_technician_choices(only_active=False)

    def queryset(self, request, queryset):
        if self.value() not in (None, 'all'):
            return queryset.filter(owner=self.value())
        else:
            return queryset


class UninstallOwnerFilter(SimpleListFilter):

    title = u'Szerelő'
    parameter_name = 'owner'

    def lookups(self, request, model_admin):
        return get_unintall_technician_choices(only_active=False)

    def queryset(self, request, queryset):
        if self.value() not in (None, 'all'):
            return queryset.filter(owner=self.value())
        else:
            return queryset


class ActiveUserFilter(SimpleListFilter):

    title = u'Felhasználó státusz'
    parameter_name = 'active'

    def lookups(self, request, model_admin):
        return (
            ('active', u'Aktív szerelők'),
            ('warehouse', u'Raktárak'),
            ('inactive', u'Nem aktív szerelők'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'inactive':
            inactive_users = User.objects.filter(is_active=False)
            return queryset.filter(owner__in=inactive_users)
        elif self.value() == 'warehouse':
            return queryset.filter(owner__isnull=True)
        else:
            if self.value() is None:
                self.used_parameters[self.parameter_name] = 'active'
            active_users = User.objects.filter(is_active=True)
            return queryset.filter(owner__in=active_users)


class NetworkOwnerFilter(SimpleListFilter):

    title = u'Szerelő'
    parameter_name = 'owner'

    def lookups(self, request, model_admin):
        return get_network_technician_choices()

    def queryset(self, request, queryset):
        if self.value() not in (None, 'all'):
            return queryset.filter(owner=self.value())
        else:
            return queryset


class PayoffFilter(SimpleListFilter):

    title = u'Elszámolás'
    parameter_name = 'payoff'

    def lookups(self, request, model_admin):
        payoff_choices = [(p.pk, unicode(p)) for p in Payoff.objects.all()]
        return [('empty', u'Nincs elszámolva')] + payoff_choices

    def queryset(self, request, queryset):
        if self.value() == 'empty':
            return queryset.filter(payoffs__isnull=True)
        elif self.value() in (None, 'all'):
            return queryset
        else:
            return queryset.filter(payoffs=self.value())


class IsClosedFilter(SimpleListFilter):

    title = u'Státusz'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return (
            (None, u''),
            ('all', u'Mind'),
            ('open', u'Nyitott'),
            ('closed', u'Lezárt'),
        )

    def choices(self, cl):
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == lookup,
                'query_string': cl.get_query_string({
                    self.parameter_name: lookup,
                }, []),
                'display': title,
            }

    def queryset(self, request, queryset):
        if self.value() is None:
            self.used_parameters[self.parameter_name] = 'open'

        if self.value() == 'open':
            return queryset.filter(status__in=(u'Új', u'Kiadva',
                                               u'Folyamatban'))
        elif self.value() == 'closed':
            return queryset.filter(status__in=(u'Lezárva - Kész',
                                               u'Lezárva - Eredménytelen',
                                               u'Duplikált'))
        elif self.value() == 'all':
            return queryset


class UninstallIsClosedFilter(SimpleListFilter):

    title = u'Státusz'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return (
            (None, u''),
            ('own_open', u'Saját (nyitott)'),
            ('own_all', u'Saját (mind)'),
            ('open', u'Nyitott'),
            ('closed', u'Lezárt'),
            ('all', u'Mind'),
        )

    def choices(self, cl):
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == lookup,
                'query_string': cl.get_query_string({
                    self.parameter_name: lookup,
                }, []),
                'display': title,
            }

    def queryset(self, request, queryset):
        if self.value() is None:
            self.used_parameters[self.parameter_name] = 'own_open'

        if self.value() == 'open':
            return queryset.filter(status__in=(u'Új', u'Kiadva',
                                               u'Folyamatban'))
        elif self.value() == 'closed':
            return queryset.filter(status__in=(u'Lezárva - Kész',
                                               u'Lezárva - Eredménytelen',
                                               u'Duplikált'))
        elif self.value() == 'own_open':
            return queryset.filter(status__in=(u'Új', u'Kiadva',
                                               u'Folyamatban'),
                                   owner=request.user)
        elif self.value() == 'own_all':
            return queryset.filter(owner=request.user)
        elif self.value() == 'all':
            return queryset


#===============================================================================
# class DeviceOwnerFilter(InputFilter):
#     parameter_name = 'deviceowner'
#     title = u'Tulajdonos'
#  
#     def queryset(self, request, queryset):
#         if self.value() is not None:
#             uid = self.value()
#             return queryset.filter(
#                 Q(uid=uid) |
#                 Q(payment__uid=uid) |
#                 Q(user__uid=uid)
#             )
#===============================================================================
