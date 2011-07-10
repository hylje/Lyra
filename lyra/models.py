# -*- encoding: utf-8 -*-

import datetime


from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from lyra import base

STYLE_CHOICES = (
    ("yellow", _(u"Yellow")),
    ("green", _(u"Green")),
    ("blue", _(u"Blue")),
    ("red", _(u"Red")),
)


class ReservationQuerySet(base.QuerySet):
    def get_for_date(self, date):
        return self.filter(
            Q(start__year=date.year,
                start__month=date.month, 
                start__day=date.day)
            | Q(stop__year=date.year,
                stop__month=date.month,
                stop__day=date.day))
    
    def get_years(self):
        return self.dates("start", "year")

    def get_months(self, year):
        return self.filter(start__year=year).dates("start", "month")
    
    def date_range(self, start_date, stop_date):
        return self.filter(
                # kokonaan sisällä
                Q(start__gte=start_date,
                    stop__lte=stop_date)
                # alkaa ennen ja loppuu alun jälkeen
                | Q(start__lt=start_date,
                    stop__gt=start_date)
                # alkaa ennen loppua ja loppuu lopun jälkeen
                | Q(start__lt=stop_date,
                    stop__gt=stop_date))

    def would_conflict(self, start_date, stop_date):
        return self.date_range(start_date, stop_date).count()

    def month(self, year, month):
        month_start = datetime.date(year, month, 1)
        next_month = month + 1
        if next_month > 12:
            next_month = 1
            next_year = year + 1
        else:
            next_year = year
        month_stop = datetime.date(next_year, next_month, 1) - datetime.timedelta(1)
        return self.date_range(month_start, month_stop)

    def year(self, year):
        year_start = datetime.date(year, 1, 1)
        year_stop = datetime.date(year+1, 1, 1) - datetime.timedelta(1)
        return self.date_range(year_start, year_stop)

class Reservation(models.Model):
    namespace = models.CharField(max_length=64, choices=base.choices())
    person = models.ForeignKey('auth.User')
    person_behalf = models.CharField(
        max_length=255, 
        blank=True,
        verbose_name=_(u"In behalf of"),
        help_text=_(u"Only if reserving by request of someone else"))
    start = models.DateTimeField(verbose_name=_(u"Reservation begins"))
    stop = models.DateTimeField(verbose_name=_(u"Reservation ends"))
    description = models.CharField(
        max_length=140,
        verbose_name=_(u"Short description"),
        help_text=_(u"Shows up on listings"))
    long_description = models.TextField(
        blank=True,
        verbose_name=_(u"Long description"),
        help_text=_(u"Shows up only on detailed view"))
    long_description_markup = models.CharField(
        default="raw",
        max_length=64)
    style = models.CharField(
        verbose_name=_(u"Style"),
        help_text=_(u"Used to distinguish the reservation"),
        max_length=32,
        choices=STYLE_CHOICES,
        default=STYLE_CHOICES[0][0])

    objects = ReservationQuerySet.as_manager()

    @models.permalink
    def get_absolute_url(self):
        return ("%s:details" % self.namespace,
                (),
                {"pk": self.pk})

    @models.permalink
    def get_week_link(self):
        year, week, weekday = self.start.isocalendar()
        return ("%s:browse_week" % self.namespace, 
                (), 
                {"year": year, "week": week})

    def get_creator_name(self):
        if self.person_behalf:
            return _(u"%(behalf)s (tehnyt: %(person)s)") % {
                "behalf": self.person_behalf, 
                "person": self.person.get_full_name()}
        return self.person.get_full_name()

    def one_day(self):
        return self.start.date() == self.stop.date()

    def is_next_week(self):
        today = datetime.date.today()
        date = self.start.date()

        if date < today:
            return False

        monday = today - datetime.timedelta(today.weekday())
        saturday = monday + datetime.timedelta(5)

        return date > saturday
        
    class Meta:
        verbose_name = _(u"Reservation")
        verbose_name_plural = _(u"Reservations")
        ordering = ('start', 'id')

base.clear_choices(Reservation)
register_app = base.make_registerer(Reservation)
ReservationQuerySet.register_app = staticmethod(register_app)
        
