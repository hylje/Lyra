class Day(dict):
    import datetime

    def css_class(self):
        classes = []
        other_days = []
        if self.get("is_offmonth"):
            other_days.append("offmonth")
        if self.is_weekend():
            other_days.append("weekend")
        if self.get("is_today"):
            return "today"
        if other_days:
            classes.append("-".join(other_days))
        if self["date"].toordinal() < self.datetime.date.today().toordinal():
            classes.append("past-day")

        return " ".join(classes)
    
    def is_weekend(self):
        return self["date"].weekday() in [5,6]
