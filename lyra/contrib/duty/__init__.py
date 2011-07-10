# -*- coding: utf-8 -*-

from django.utils.translation import ugettext as _
from django import forms

from lyra.contrib import drive 
from lyra.contrib.duty import models

def date_range(begin, end):
    assert end >= begin

    cur = begin
    while cur <= end:
        yield cur 
        cur += datetime.timedelta(1)

class WeekFacade(object):
    from django.core import urlresolvers

    def __init__(self, namespace, date):
        self.year, self.week, x_ = date.isocalendar()
        self.namespace = namespace

    def get_absolute_url(self):
        return self.urlresolvers.reverse(
            "%s:browse_week" % self.namespace,
            kwargs={"year": self.year, "week": self.week})
            

class DutyReservation(forms.Form):
    period_start_date = forms.DateField(
        label=_(u"Päivystysjakson ensimmäinen päivämäärä"))
    period_stop_date = forms.DateField(
        label=_(u"Päivystysjakson viimeinen päivämäärä"))
    period_time_start = forms.TimeField(
        label=_(u"Päivystystunnit jaksolla alkaen"))
    period_time_stop = forms.TimeField(
        label=_(u"Päivystystunnit jaksolla kunnes"))

    person = forms.ModelChoiceField(
        queryset=models.DutyPerson.objects.all(),
        label=_(u"Takapäivystäjä"),
        help_text=_(u"Lisää takapäivystäjiä ylläpitopaneelista"))

    def __init__(self, *args, **kwargs):
        self.person = kwargs.pop("person")
        self.namespace = kwargs.pop("namespace")
        self.instance = kwargs.pop("instance")
        self.queryset = kwargs.pop("queryset")
        super(DutyReservation, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(DutyReservation, self).clean()

        if all(k in cleaned_data for k in ("period_start_date", 
                                           "period_stop_date",
                                           "period_time_start",
                                           "period_time_stop")):
            if cleaned_data["period_start_date"] > cleaned_data["period_stop_date"]:
                (self._errors
                     .setdefault("period_start_date", self.error_class())
                     .append(_("Varauksen tulee alkaa ennen kuin se loppuu.")))
            if cleaned_data["period_time_start"] > cleaned_data["period_time_stop"]:
                (self._errors
                     .setdefault("period_time_start", self.error_class())
                     .append(_("Varauksen tulee alkaa ennen kuin se loppuu.")))
                

        return cleaned_data        

    def save(self):
        if not self.is_valid:
            raise ValueError
        
        data = self.cleaned_data

        for date in date_range(data["period_start_date"],
                               data["period_stop_date"]):
            models.Reservation.objects.create(
                namespace=self.namespace,
                person=self.person,
                start=datetime.datetime.combine(date, data["period_time_start"]),
                stop=datetime.datetime.combine(date, data["period_time_stop"]),
                description=u"%s puh. tfn. %s" % (data["person"].user.get_full_name(), data["person"].phone))
        
        return WeekFacade(self.namespace, data["period_start_date"])

class DutyApp(drive.DriveApp):
    from django.conf.urls import defaults as urlconf
    
    app_name = "duty"

    def get_app_name(self):
        return _(u"Takapäivystys")

    def user_can_create(self, request):
        return request.user.has_perm("lyra.add_reservation")

    def user_can_edit(self, request, reservation):
        return request.user.has_perm("lyra.change_reservation")

    def user_can_delete(self, request, reservation):
        return request.user.has_perm("lyra.delete_reservation")

    class crud_app(drive.DriveApp.crud_app):
        import datetime

        reservation_form_create = DutyReservation

        def _get_urls(self):
            patterns = super(DutyApp.crud_app, self)._get_urls()
            patterns += self.urlconf.patterns('', *[
                    self.urlconf.url('^%s/(?P<year>\d{4})/(?P<month>\d+)/$' % _("tyoaika"), 
                                     self.month_report, 
                                     name="month_report"),
                    ])
            return patterns

        def month_report(self, request, year, month):
            is_forbidden = self.app.check_forbidden(request, ["view"])
            if is_forbidden:
                return is_forbidden

            year, month = int(year), int(month)
            start = self.datetime.date(year, month, 1)
            if month < 12:
                stop = self.datetime.date(year, month+1, 1)
            else:
                stop = self.datetime.date(year+1, 1, 1)

            reservations = self.app.queryset.date_range(start, stop)
                
            return self.app.get_response(
                request,
                template="month_report",
                context={
                    "reservations": reservations,
                    "date": start
                    })
