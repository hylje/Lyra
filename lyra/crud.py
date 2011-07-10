from lyra import base

from django.utils.translation import ugettext as _
from django.views.generic import edit
from django.views.generic import detail

class FormArgumentsMixin(object):
    import datetime

    def get_initial(self):
        initial = super(FormArgumentsMixin, self).get_initial()
        try:
            day = self.request.GET.get("day", u"")
            initial_date = self.datetime.datetime.strptime(
                day, "%Y-%m-%d"
                )
            initial_date = initial_date.replace(hour=8)
            initial.update({
                    "start": initial_date,
                    "stop": initial_date})      
        except ValueError:
            pass

        return initial
            
    def get_form_kwargs(self):
        args = super(FormArgumentsMixin, self).get_form_kwargs()
        args.update({
                "person": self.request.user,
                "namespace": self.app.namespace,
                "queryset": self.app.queryset
                })
        return args


class ReservationCreate(base.AppAwareTemplate, 
                        base.AppAwareSecurityMixin,
                        FormArgumentsMixin,
                        edit.BaseCreateView):
    permissions = ["view", "create"]
    template_name = "reserve"

class ReservationUpdate(base.AppAwareTemplate, 
                        base.AppAwareObjectSecurityMixin, 
                        FormArgumentsMixin,
                        edit.BaseUpdateView):
    permissions = ["view", "edit"]
    template_name = "reserve"

class ReservationDeletion(base.AppAwareTemplate, 
                          base.AppAwareObjectSecurityMixin,
                          detail.SingleObjectMixin,
                          edit.FormView):
    permissions = ["view", "delete"]
    template_name = "remove"
    
    def get_success_url(self):
        return self.object.get_week_link()

    def get(self, *args, **kwargs):
        self.object = self.get_object()
        return super(ReservationDeletion, self).get(*args, **kwargs)

    def form_valid(self, form):
        self.object = self.get_object()
        self.object.delete()
        return super(ReservationDeletion, self).form_valid(form)

    def form_invalid(self, form):
        self.object = self.get_object()
        return super(ReservationDeletion, self).form_invalid(form)

class ReservationDetail(base.AppAwareTemplate,
                        base.AppAwareObjectSecurityMixin,
                        detail.BaseDetailView):
    template_name = "details"

class Crud(base.SubApp):
    import datetime

    from django import shortcuts
    from django import http
    from django.conf.urls import defaults as urlconf

    from lyra import forms

    reservation_form = forms.ReservationExclusiveEnable
    confirm_form = forms.ConfirmForm

    create = ReservationCreate
    update = ReservationUpdate
    delete = ReservationDeletion
    detail = ReservationDetail

    def _get_urls(self):
        return self.urlconf.patterns('', *[
            self.urlconf.url(
                    '^$', 
                    self.create.as_view(
                        app=self.app,
                        view_name="reserve",
                        form_class=getattr(self, 
                                           "reservation_form_create", 
                                           self.reservation_form)), 
                    name="reserve"),
            self.urlconf.url(
                    '^(?P<pk>\d+)/$',
                    self.detail.as_view(
                        app=self.app,
                        view_name="details"),
                    name="details"),
            self.urlconf.url(
                    '^(?P<pk>\d+)/%s/$' % (_("muokkaa")),
                    self.update.as_view(
                        app=self.app,
                        view_name="reserve",
                        form_class=getattr(self, 
                                           "reservation_form_edit", 
                                           self.reservation_form)), 
                    name="reserve"),
            self.urlconf.url(
                    '^(?P<pk>\d+)/%s/$' % (_("poista")),
                    self.delete.as_view(
                        app=self.app,
                        view_name="remove",
                        form_class=self.confirm_form), 
                    name="remove")])
