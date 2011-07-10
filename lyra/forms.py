# -*- encoding: utf-8 -*-

import datetime

from django import forms
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.core import exceptions as django_exceptions

from lyra import models

class Reservation(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.person = kwargs.pop("person")
        self.namespace = kwargs.pop("namespace")
        self.queryset = kwargs.pop("queryset")
        super(Reservation, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(Reservation, self).clean()

        if all(k in cleaned_data for k in ("start", "stop")):
            start = cleaned_data["start"]
            stop = cleaned_data["stop"]
            if start > stop:
                (self._errors
                     .setdefault("start", self.error_class())
                     .append(_("The reservation should begin before it ends")))

        return cleaned_data

    def save(self, commit=True, **kwargs):
        obj = super(Reservation, self).save(commit=False, **kwargs)
        
        if not obj.pk:
            obj.person = self.person
            obj.namespace = self.namespace

        if commit:
            obj.save()
        return obj            

    class Meta:
        model = models.Reservation
        exclude = ("namespace", "person", "long_description_markup")
        widgets = {
            "style": forms.Select(attrs={"class": "schedule_style"}),
            }

    class Media:
        js = ("shared/js/sivari.stylepreview.js",)
    
class ReservationExclusive(Reservation):
    def toggle_enabled(self, cleaned_data):
        return (not hasattr(self, "exclusive")
                and cleaned_data.get("exclusive"))

    def clean(self):
        cleaned_data = super(ReservationExclusive, self).clean()

        start_date = cleaned_data.get("start")
        stop_date = cleaned_data.get("stop")
        if start_date and stop_date and self.toggle_enabled(cleaned_data):
            would_conflict = self.queryset.date_range(
                start_date, stop_date)
            if self.instance.pk: 
                would_conflict = would_conflict.exclude(pk=self.instance.pk)
            if would_conflict.count():
                (self._errors
                     .setdefault("start", self.error_class())
                     .append(_(u"The reservation would conflict with %(conflict_count)s "
                               u"other reservations.") % {
                            "conflict_count": would_conflict}))

        return cleaned_data        

class ReservationExclusiveEnable(ReservationExclusive):
    exclusive = forms.BooleanField(
        label=_(u"No overlap"),
        required=False)

class ReservationExclusiveDisable(ReservationExclusive):
    exclusive = forms.BooleanField(
        label=_(u"No overlap"),
        required=False,
        initial=True)

class ConfirmForm(forms.Form):
    confirm = forms.BooleanField()
