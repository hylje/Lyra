import django

major, minor, patch, _, _ = django.VERSION

if major == 1 and minor < 3:
    raise Exception("Lyra requires Django 1.3 or later. Currently installed: %s.%s" % (major, minor))

from lyra import views

root = views.Lyra()
