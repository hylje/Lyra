from lyra import base

from django.utils.translation import ugettext as _

class Browse(base.SubApp):
    import datetime
    import calendar as calendar_mod

    from django.conf.urls import defaults as urlconf
    
    from lyra import dayplanner  
    from lyra import day

    week_display = dayplanner.WeekBrowse
    day_display = dayplanner.DayBrowse
    day_class = day.Day
    
    def __init__(self, *args, **kwargs):
        super(Browse, self).__init__(*args, **kwargs)
        self.calendar = self.calendar_mod.Calendar()

    def _get_urls(self):
        return self.urlconf.patterns('', *[
            self.urlconf.url('^$', self.browse_index, name="browse_index"),
            self.urlconf.url(
                    '^(?P<year>\d{4})/$',
                    self.browse_year, name="browse_year"),
            self.urlconf.url(
                    '^(?P<year>\d{4})/%s(?P<week>\d{1,2})/$' % (_(u"week")),
                    self.week_display.as_view(app=self.app),
                    name="browse_week"),
            self.urlconf.url(
                    '^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$',
                    self.day_display.as_view(app=self.app),
                    name="browse_day"),
            self.urlconf.url(
                    '^(?P<year>\d{4})/(?P<month>\d{1,2})/',
                    self.browse_month, name="browse_month"),])

    def browse_index(self, request):
        is_forbidden = self.app.check_forbidden(request, ["view"])
        if is_forbidden:
            return is_forbidden

        this_year = self.datetime.date.today().year
        next_year_date = self.datetime.datetime(this_year+1, 1, 1)
        all_years = list(self.app.queryset.get_years())
        if next_year_date not in all_years:
            all_years.append(next_year_date)
            all_years.sort()

        return self.app.get_response(
            request,
            template="index", 
            context={
                "years": [
                    {"year": year,
                     "link": self.app.reverse("browse_year", {
                                "year": year.year}),
                     "reservation_count": self.app.queryset.year(year.year).count()}
                    for year in all_years],
                "app_name": self.app.get_app_desc(), 
                },)

    def browse_year(self, request, year):
        is_forbidden = self.app.check_forbidden(request, ["view"])
        if is_forbidden:
            return is_forbidden
        year = int(year)
        
        return self.app.get_response(
            request,
            template="browse_year",
            context={
                "year": year,
                "next_year_link": self.app.reverse("browse_year", {"year": year+1}),
                "prev_year_link": self.app.reverse("browse_year", {"year": year-1}),
                "months": [
                    {"date": self.datetime.date(year, m, 1),
                     "link": self.app.reverse("browse_month", {
                                "month": m, 
                                "year": year}),
                     "reservation_count": self.app.queryset.month(year, m).count()}
                    for m 
                    in range(1, 13)],
                "app_name": self.app.get_app_desc(),  
                "index_link": self.app.reverse("browse_index"),
             },)

    def browse_month(self, request, year, month):
        is_forbidden = self.app.check_forbidden(request, ["view"])
        if is_forbidden:
            return is_forbidden

        def getweek(week):
            date = week[0]
            year, week, weekday = date.isocalendar()
            return week

        def getyear(week):
            date = week[0]
            year, week, weekday = date.isocalendar()
            return year

        year, month = int(year), int(month)

        today = self.datetime.date.today()
        weeks = [{"week": getweek(week),
                  "days": [self.day_class({
                        "date": d, 
                        "events": self.app.queryset.get_for_date(date=d),
                        "is_today": d == today,
                        "is_offmonth": d.month != month})
                           for d in week],
                  "link": self.app.reverse("browse_week", {
                        "year": getyear(week),
                        "week": getweek(week)})} 
                 
                 for week in self.calendar.monthdatescalendar(year, month)]

        next_month = month + 1
        next_year = year
        if next_month > 12:
            next_month = 1
            next_year = year + 1 
        
        prev_month = month - 1
        prev_year = year
        if prev_month < 1:
            prev_month = 12
            prev_year = year - 1 

        return self.app.get_response(
            request,
            template="browse_month",
            context={
                "weeks": weeks,
                "year": year,
                "month": self.datetime.date(year, month, 1),
                "prev_month_link": self.app.reverse("browse_month", {
                        "month": prev_month,
                        "year": prev_year}),
                "prev_year": prev_year,
                "prev_month": prev_month,
                "next_month_link": self.app.reverse("browse_month", {
                        "month": next_month,
                        "year": next_year}),
                "next_year": next_year,
                "next_month": next_month,
                "reserve_link": self.app.reverse("reserve"),
                "year_link": self.app.reverse("browse_year", {"year": year}),
                "app_name": self.app.get_app_desc(),
                },)                
