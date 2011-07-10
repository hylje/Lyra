from django.views.generic import base as views_base

def quarts(time):
    """quarters from 0:00, rounded up
    
    values range from 0 (0:00-0:15) to 95 (23:45-0:00)"""
    return time.hour * 4 + time.minute // 15

def get_weekdays(year, week):
    import datetime
    first_day = datetime.date(year, 1, 1) 
    monday = first_day + datetime.timedelta(
        days=-first_day.weekday(), 
        weeks=week)
    return [monday+datetime.timedelta(days=i) for i in range(7)]

class DayPlanner(views_base.View):
    import datetime

    from lyra import day

    app = None

    QUARTER_HEIGHT = 15 #px
    DISPLAY_WEEKENDS = True
    
    day_class = day.Day

    template_name = "browse_week"

    def render(self, weekdays, extra_context=None, template_name=None):
        if extra_context is None:
            extra_context = {}

        is_forbidden = self.app.check_forbidden(self.request, ["view"])
        if is_forbidden:
            return is_forbidden

        (self.months_mentioned, 
         self.years_mentioned) = self.collect_months_and_years(weekdays)
        
        today = self.datetime.date.today()
        days = [self.day_class({
                    "date": d, 
                    "events": self.process_day_events(
                        d,
                        self.app.queryset.get_for_date(date=d)),
                    "link": self.app.reverse("browse_day", {
                            "year": d.year,
                            "month": d.month,
                            "day": d.day}),
                    "is_today": d == today})
                for d in weekdays]
        
        self.min_quart, self.max_quart = self.get_quart_bounds(days)
        self.business_hours = self.get_business_hours()
            
        if self.business_hours:
            self.days_columns = self.generate_columns(days)
        else:
            self.days_columns = []

        return self.app.get_response(
            self.request,
            template=template_name or self.template_name,
            context=dict({
                "days": self.days_columns,
                "months_mentioned": self.months_mentioned,
                "years_mentioned": self.years_mentioned,
                "business_hours": self.business_hours,
                "hour_height": self.QUARTER_HEIGHT * 4,
                "table_max_height": (self.QUARTER_HEIGHT * 4 
                                     * (len(self.business_hours))),
                "reserve_link": (self.app.user_can_create(self.request) 
                                 and self.app.reverse("reserve")),
                "app_name": self.app.get_app_name(),}, 
                         **extra_context))

    def annotate_vacancies(self, column):
        new_column = []
        current_quart = self.min_quart

        for event in column:
            event_quarts = quarts(event["stop"]) - quarts(event["start"])
            event.update({
                    "is_vacant": False,
                    "height": event_quarts * self.QUARTER_HEIGHT,
                    "top": ((quarts(event["start"]) - self.min_quart) 
                            * self.QUARTER_HEIGHT),
                    "quarts": event_quarts,
                    })
            new_column.append(event)

        return new_column
    
    def collect_months_and_years(self, weekdays):
        months_mentioned = []
        years_mentioned = []
        for d in (weekdays[0], weekdays[-1]):
            if d.month not in [m["date"].month for m in months_mentioned]:
                months_mentioned.append(
                    {"date": d,
                     "link": self.app.reverse("browse_month", {
                                "year": d.year, 
                                "month": d.month})})
            if d.year not in [y["date"].year for y in years_mentioned]:
                years_mentioned.append(
                    {"date": d,
                     "link": self.app.reverse("browse_year", {
                                "year": d.year})})
                    
        return months_mentioned, years_mentioned

    def get_quart_bounds(self, days):
        min_quart = 24*4
        max_quart = 0

        for day in days:
            min_quart = min([min_quart] + [
                    quarts(e["start"]) for e in day["events"]])
            max_quart = max([max_quart] + [
                    quarts(e["stop"]) for e in day["events"]])
    
        min_quart -= min_quart % 4
        max_quart -= max_quart % 4 - 8
            
        return min_quart, max_quart

    def get_business_hours(self):
        if self.min_quart > self.max_quart:
            # no (well-formed) events
            business_hours = []
        else:
            business_hours = [a % 24 for a in range(self.min_quart//4, 
                                                    self.max_quart//4)]
        return business_hours

    def conflicts(self, start1, start2, end1, end2):
        if start1 < start2 < end1:
            return True
        if start1 < end2 < end1:
            return True
        return False

    def fits(self, list_, event):
        return not any(self.conflicts(event["start"], event["stop"], 
                                      e["start"], e["stop"])
                       for e in list_)

    def split_columns(self, events):
        # list of single empty list to ensure every day 
        # has at least one column
        columns = [[]]
        for event in events:
            for column in columns:
                if self.fits(column, event):
                    column.append(event)
                    break
            else:
                columns.append([event])
                
        return columns        

    def process_day_events(self, date, queryset):
        return [dict(vars(e), **{
                    # multi day events show up multiple times, for each day
                    "start": max([
                            e.start, 
                            self.datetime.datetime.combine(
                                date, 
                                self.datetime.time(hour=0, minute=0, second=0))]),
                    "stop": min([
                            e.stop,
                            self.datetime.datetime.combine(
                                date, 
                                self.datetime.time(hour=23, minute=59, second=59))]),
                    "creator_name": e.get_creator_name(),
                    "update_link": self.app.reverse(
                        "reserve", 
                        kwargs={"pk": e.pk}),
                    "remove_link": self.app.reverse(
                        "remove", 
                        kwargs={"pk": e.pk}),
                    "can_update": self.app.user_can_edit(self.request, e),
                    "can_remove": self.app.user_can_delete(self.request, e),
                    "link": e.get_absolute_url(),
                    "one_day": e.one_day(),
                    "instance": e,
                })
                for e 
                in queryset]

    def generate_columns(self, days):
        for day in days:
            day["event_columns"] = [
                self.annotate_vacancies(column) 
                for column in self.split_columns(day["events"])]
        return days

class WeekBrowse(DayPlanner):
    def get(self, request, year, week, template_name=None, extra_context={}):
        year, week = int(year), int(week)
        weekdays = get_weekdays(year, week)

        if not self.DISPLAY_WEEKENDS:
            weekdays = weekdays[:5]
            
        monday = weekdays[0]
        (prev_year, 
         prev_week, 
         x) = (monday - self.datetime.timedelta(7)).isocalendar()
        (next_year,
         next_week,
         x) = (monday + self.datetime.timedelta(7)).isocalendar()

        return self.render(
            weekdays, 
            extra_context=dict({
                "week": week,
                "year": year,
                "prev_week_link": self.app.reverse("browse_week", {
                        "week": prev_week,
                 "year": prev_year,}),
                "prev_week": prev_week,
                "next_week_link": self.app.reverse("browse_week", {
                        "week": next_week,
                        "year": next_year}),
                "next_week": next_week,
                }, **extra_context),
            template_name=template_name)

class DayBrowse(DayPlanner):
    template_name = "browse_day"

    def get(self, request, year, month, day):
        date = self.datetime.date(int(year), int(month), int(day))

        tomorrow = date + self.datetime.timedelta(1)
        yesterday = date - self.datetime.timedelta(1)
 
        return self.render([date], extra_context={
                "date": date,
                "next_day": tomorrow,
                "next_day_link": self.app.reverse(
                    "browse_day", {"year": tomorrow.year, 
                                   "month": tomorrow.month,
                                   "day": tomorrow.day}),
                "prev_day": yesterday,
                "prev_day_link": self.app.reverse(
                    "browse_day", {"year": yesterday.year,
                                   "month": yesterday.month,
                                   "day": yesterday.day}),
                })

