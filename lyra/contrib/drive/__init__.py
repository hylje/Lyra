from django.utils.translation import ugettext as _

from lyra import views

class DriveApp(views.Lyra):
    app_name = "drive"

    class crud_app(views.ScheduleApp.crud_app):
        from lyra import forms

        reservation_form = forms.ReservationExclusiveDisable
    
    def get_app_name(self):
        return _(u"Ajonvarauskirja")

    def user_can_view(self, request, reservation=None):
        return request.user.is_authenticated()

    def user_can_edit(self, request, reservation):
        return (super(DriveApp, self).user_can_edit(request, reservation)
                or request.user.has_perm("lyra.change_reservation_lesser"))

    def user_can_delete(self, request, reservation):
        return (super(DriveApp, self).user_can_delete(request, reservation)
                or request.user.has_perm("lyra.delete_reservation_lesser"))

    def user_can_create(self, request):
        return request.user.is_authenticated()
