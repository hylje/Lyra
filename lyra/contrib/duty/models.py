from django.utils.translation import ugettext_lazy as _
from django.db import models
    
class DutyPerson(models.Model):
    user = models.ForeignKey('auth.User', 
                             verbose_name=_(u"Käyttäjätunnus"))
    phone = models.CharField(max_length=127, 
                             verbose_name=_(u"Puhelinnumero"))
    accounting_no = models.CharField(
        max_length=127,
        verbose_name=_(u"Tiliöintinumero"),
        default=u"")

    def __unicode__(self):
        return unicode(self.user)

    class Meta:
        verbose_name = _(u"Takapäivystäjä")
        verbose_name_plural = _(u"Takapäivystäjiä")
