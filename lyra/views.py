# -*- encoding: utf-8 -*-

import calendar
import datetime

from django.utils import translation
from django.utils.translation import ugettext as _
from django.contrib.auth import decorators as auth_decorators
from django.utils.decorators import method_decorator
from django.views.generic import base as views_base

from lyra import base

login_required_m = method_decorator(auth_decorators.login_required)

class PermissionError(Exception):
    def __init__(self, *args, **kwargs):
        self.reason = kwargs.pop("reason", "admin")
        super(PermissionError, self).__init__(*args, **kwargs)

class Lyra(base.App):
    import datetime

    from django import http
    from django import shortcuts
    from django import template
    from django.conf import settings
    from django.conf.urls import defaults as urlconf
    from django.core import urlresolvers
    from django.db.models import Q

    from lyra import models
    from lyra import forms
    from lyra import browse
    from lyra import crud

    model = models.Reservation
    app_name="lyra"

    # subapplications
    browse_class = browse.Browse
    crud_class = crud.Crud

    # errors
    perm_error = PermissionError

    def get_app_desc(self):
        return _(u"Calendar")

    def __init__(self, *args, **kwargs):
        self.model.objects.register_app(
            (self.namespace, self.get_app_desc()), 
            self.app_name)

        self._queryset = None

        self.browser = self.browse_class(app=self)
        self.crud = self.crud_class(app=self)

    @property
    def queryset(self):
        if self._queryset:
            return self._queryset

        qs = self._queryset = self.model.objects.filter(
            namespace=self.namespace)
        return qs
    
    def _get_urls(self):
        patterns = self.urlconf.patterns('', *[
                self.urlconf.url('^$', self.landing, name="landing"),
                self.urlconf.url('^%s/' % _(u"date"), 
                    self.urlconf.include(self.browse.urls)),
                self.urlconf.url(
                    '^%s/' % _(u"reservation"),
                    self.urlconf.include(self.crud.urls))
                ])

        return patterns

    def landing(self, request):
        today = self.datetime.date.today()
        year, week, weekday = today.isocalendar()

        return self.browser.week_display.as_view(app=self)(
            request, 
            year, 
            week, 
            template_name="landing")

    def user_can_create(self, request):
        return request.user.is_authenticated()

    def user_can_edit(self, request, res):
        user = request.user
        return (user.is_authenticated() 
                and user == res.person)
    
    def user_can_delete(self, request, res):
        user = request.user
        return (user.is_authenticated() 
                and user == res.person)

    def user_can_view(self, request, obj=None): 
        return True
    
    def check_forbidden(self, request, perm_list, obj=None):
        def try_meth(m):
            try:
                return m(request, obj)
            except TypeError:
                try:
                    return m(request)
                except TypeError:
                    pass
                raise
        
        for perm in perm_list:
            perm_method = getattr(self, "user_can_%s" % perm)
            if not perm_method:
                raise ValueError("unknown permission %s" % perm)

            try:
                allowed = try_meth(perm_method)
                if not allowed:
                    return self.forbidden(request)
            except self.perm_error, exc:
                return self.forbidden(request, exc.reason)
        
    def forbidden(self, request, reason="admin"):
        return self.get_response("forbidden", {"reason": reason}) 

    def get_a_couple_events(self):
        now = self.datetime.datetime.now()
        return (self.queryset
                .filter((self.Q(start__lte=now)
                         & self.Q(stop__gte=now))
                        | self.Q(start__gt=now))
                .order_by("start"))[:4]
