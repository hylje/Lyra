# -*- coding: utf-8 -*-

from django.utils.translation import ugettext as _
from django import forms

from lyra import views
from lyra import dayplanner

class FridayForm(forms.Form):
    lunch_main = forms.CharField(
        label=_(u"Lunch main course"),
        required=False)
    lunch_other = forms.CharField(
        widget=forms.Textarea, 
        required=False,
        label=_(u"Lunch side courses"))

    def __init__(self, *args, **kwargs):
        self.date = kwargs.pop("date")
        self.queryset = kwargs.pop("queryset")
        self.new_object = kwargs.pop("new_object")
        
        kwargs["initial"] = self.get_initial()

        super(FridayForm, self).__init__(*args, **kwargs)

    def get_initial(self):
        lunch = self.get_lunch_reservation()
        return {
            "lunch_main": lunch.description,
            "lunch_other": lunch.long_description}

    def get_lunch_reservation(self):
        start = datetime.datetime.combine(self.date, datetime.time(11, 15))

        try:
            return self.queryset.get(start=start)
        except django_exceptions.ObjectDoesNotExist:
            return self.new_object(start=start, stop=start.replace(hour=12, minute=0))

    def save(self, commit=True):
        res = self.get_lunch_reservation()
        res.description = self.cleaned_data["lunch_main"]
        res.long_description = self.cleaned_data["lunch_other"]
        if commit:
            res.save()
        return [res]

class DayForm(FridayForm):
    dinner_main = forms.CharField(
        label=_(u"Dinner main course"),
        required=False)
    dinner_other = forms.CharField(
        widget=forms.Textarea, 
        required=False,
        label=_(u"Dinner side courses"))

    def get_initial(self):
        dinner = self.get_dinner_reservation()

        return dict(super(DayForm, self).get_initial(),
                    dinner_main=dinner.description,
                    dinner_other=dinner.long_description)

    def get_lunch_reservation(self):
        start = datetime.datetime.combine(self.date, datetime.time(11, 0))

        try:
            return self.queryset.get(start=start)
        except django_exceptions.ObjectDoesNotExist:
            return self.new_object(start=start, stop=start.replace(hour=12, minute=45))

    def get_dinner_reservation(self):
        start = datetime.datetime.combine(self.date, datetime.time(16, 0))

        try:
            return self.queryset.get(start=start)
        except django_exceptions.ObjectDoesNotExist:
            return self.new_object(start=start, stop=start.replace(hour=17))

    def save(self, commit=True):
        reservations = super(DayForm, self).save(commit=False)
        res = self.get_dinner_reservation()
        res.description = self.cleaned_data["dinner_main"]
        res.long_description = self.cleaned_data["dinner_other"]
        reservations.append(res)
        if commit:
            for res in reservations:
                res.save()
        return reservations

class Menu(views.Lyra):
    app_name = "food"
    
    def get_app_name(self):
        return _(u"Menu")

    class crud_app(views.Lyra.crud_app):
        from django import http

        from lyra import models

        day_form = DayForm
        friday_form = FridayForm
        reservation_model = models.Reservation

        def _get_urls(self):
            patterns = super(Menu.crud_app, self)._get_urls()
            patterns += self.urlconf.patterns('', *[
                    self.urlconf.url('^%s/(?P<year>\d{4})/%s(?P<week>\d+)/$' % (_("viikon-varaus"), _("viikko")), 
                                     self.reserve_week,
                                     name="reserve_week"),
                    ])
            return patterns

        
        def reserve_week(self, request, year, week):
            is_forbidden = self.app.check_forbidden(
                request, ["view", "create"])
            if is_forbidden:
                return is_forbidden

            year, week = int(year), int(week)

            weekdays = dayplanner.get_weekdays(year, week)
            monthu = weekdays[:4]
            fri = weekdays[4]

            def new_object(**kwargs):
                our_kwargs = dict(kwargs, **{"person": request.user, 
                                             "namespace": self.app.namespace})
                return self.reservation_model(**our_kwargs)

            if request.method == "POST":
                forms = []
                for i, date in enumerate(monthu):
                    forms.append(self.day_form(request.POST, 
                                               date=date, 
                                               prefix=i, 
                                               queryset=self.app.queryset,
                                               new_object=new_object))
                forms.append(self.friday_form(request.POST, 
                                              date=fri, 
                                              prefix=i+1,
                                              queryset=self.app.queryset,
                                              new_object=new_object))

                if all(f.is_valid() for f in forms):
                    for form in forms:
                        form.save()
                    return self.http.HttpResponseRedirect(
                        self.app.reverse("browse_week", {
                                "year": year, 
                                "week": week}))
            else:
                forms = []
                for i, date in enumerate(monthu):
                    forms.append(self.day_form(
                            date=date, 
                            prefix=i, 
                            queryset=self.app.queryset, 
                            new_object=new_object))
                forms.append(self.friday_form(
                        date=fri,
                        prefix=i+1, 
                        queryset=self.app.queryset, 
                        new_object=new_object))

            return self.app.get_response(
                request,
                template="reserve_week",
                context={"forms": forms,
                         "app_name": self.app.get_app_name()})


    class browser_app(views.Lyra.browse_app):
        class week_display(views.Lyra.browse_app.week_display):
            import datetime

            DISPLAY_WEEKENDS = False
        
            BREAKFAST_EVENTS = {
                0: {"description": u"Kaurapuuro"},
                1: {"description": u"Ruishiutalepuuro",},
                2: {"description": u"Neljänviljanpuuro"},
                3: {"description": u"Ohrahiutalepuuro"},
                4: {"description": u"Mannapuuro"},
                }

            BREAKFAST_COMMON = {
                "long_description": u"Kahvi, tee",
                "start": datetime.time(7),
                "stop": datetime.time(8, 30),
                "style": "yellow",
                }
            
            def process_day_events(self, date, queryset):
                events = (super(FoodSchedule.browser_app.week_display, 
                                self)
                          .process_day_events(date, queryset))

                meaningful_events = [e for e in events 
                                     if e.get("description")
                                     or e.get("long_description")]
                
                if meaningful_events:
                    breakfast = dict(self.BREAKFAST_EVENTS[date.weekday()],
                                     **self.BREAKFAST_COMMON)
                
                    for k in ["start", "stop"]:
                        breakfast[k] = self.datetime.datetime.combine(date, breakfast[k])
                        
                    return [breakfast] + meaningful_events
                return []

            ROW_LABEL_NAMES = ["start", "stop", "label"]
            ROW_LABELS = [
                (datetime.time(7, 0), datetime.time(8, 45), u"Aamiainen"),
                (datetime.time(11, 0), datetime.time(12, 45), u"Lounas"),
                (datetime.time(16, 0), datetime.time(17, 0), u"Päivällinen")
                ]

            def week_table_rows(self, year, week):
                columns = [[None] + [
                    dict(zip(self.ROW_LABEL_NAMES, labels)) 
                    for labels in self.ROW_LABELS]]
                weekdays = dayplanner.get_weekdays(int(year), int(week))[:5]

                for weekday in weekdays:
                    col = [{"date": weekday}]
                    events = self.process_day_events(
                        weekday, 
                        self.app.queryset.get_for_date(weekday))

                    for start, stop, label in self.ROW_LABELS: 
                        es = [e for e in events 
                             if e["start"].time() >= start
                             and e["stop"].time() <= stop]
                        if es:
                            col.append(es[0])
                        else:
                            col.append(None)
                            
                    if all(not cell for cell in col[1:]):
                        col[2] = {
                            "description": _(u"(Päivä jätetty tyhjäksi)")
                            }

                    columns.append(col)

                return zip(*columns)

            def get(self, request, year, week, *args, **kwargs):
                if "print" in request.GET:
                    kwargs["template_name"] = "week_print"
                    kwargs["extra_context"] = {
                        "table_rows": self.week_table_rows(year, week)
                        }

                return super(Lyra.browse_app.week_display, self).get(
                    request, year, week, *args, **kwargs)
