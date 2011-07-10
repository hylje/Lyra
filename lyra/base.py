import functools
import itertools

from django.db import models
from django.views.generic import base as views_base
from django.template import loader
from django import template as template_module
from django import http

_namespace_registry = {}

class TemplatePrefixMeta(type):
    def __new__(meta, classname, bases, attrs):
        if attrs.get("app_name") and not attrs.get("template_prefix"):
            attrs["template_prefix"] = attrs["app_name"]
        return type.__new__(meta, classname, bases, attrs)
    
class HasUrls(object):   
    @property
    def urls(self):
        patterns = self._get_urls()
        return patterns, self.app_name, self.namespace

    def _get_urls(self):
        raise NotImplementedError
     
class SubApp(HasUrls):
    @property
    def urls(self):
        return self._get_urls()

    def __init__(self, app):
        self.app = app

class App(HasUrls):
    __metaclass__ = TemplatePrefixMeta

    from django.core import urlresolvers

    app_name = None
    extra_context = {}
    app_dict = {}
    template_prefix = None

    def __init__(self, namespace=None, app_name=None,
                 app_namespace=None, template_prefix=None, 
                 parent=None):
        if self.app_name is None and app_name is None:
            raise ValueError("Must define app_name in either "
                             "class scope or in instantiation")
        if app_name is not None:
            self.app_name = app_name 

        if template_prefix:
            self.template_prefix = template_prefix

        self.namespace = namespace or self.app_name
        self.app_namespace = app_namespace or self.namespace

        self.__class__.app_dict.setdefault(self.app_name, []).append(self)
        _namespace_registry[self.namespace] = self
        self.parent = parent

    @staticmethod
    def get_by_namespace(self, namespace):
        return _namespace_registry.get(namespace)

    def get_template_names(self, template_select, 
                           denominator=None, extensions=["html"]):
        some_prefixes = [getattr(p, "template_prefix", None) 
                         for p 
                         in self.__class__.__mro__]
        prefixes = [self.template_prefix] + list(filter(bool, some_prefixes))

        candidates = []

        for (prefix, template, ext
             ) in itertools.product(prefixes, template_select, extensions):
            if denominator is not None:
                candidates.append(
                    "%(app_name)s/custom/%(denominator)s/%(template)s.%(ext)s" % {
                        "app_name": prefix,
                        "denominator": denominator,
                        "template": template,
                        "ext": ext}
                    )
                
            candidates.append(
                "%(app_name)s/%(template)s.%(ext)s" % {
                    "app_name": prefix,
                    "template": template,
                    "ext": ext},
                )

        for (template, ext 
             ) in itertools.product(template_select, extensions):    
            candidates.append(
                "%(template)s.%(ext)s" % {
                    "template": template,
                    "ext": ext,
                    }
                )
            
        return candidates
        

    def get_response(self, request, context={}, template=None,
                     denominator=None, extend_template=None,
                     template_select=None):

        if extend_template is None:
            extend_template = getattr(self, "base_template", "base")

        if template and template_select is None:
            template_select = [template]
        elif template_select is None:
            raise ValueError("provide one of template or "
                             "template_select, not both or neither")
        
        tpl = loader.select_template(
            self.get_template_names(template_select, denominator))

        base_context = dict(
            self.extra_context,
            **{
                "base": loader.select_template(
                    self.get_template_names([extend_template], denominator))}
            )
        context = dict(base_context, **context)
        ctx = template_module.RequestContext(request, context)
        ctx.current_app = self.app_namespace

        return http.HttpResponse(tpl.render(ctx))

    def reverse(self, view_name, kwargs={}):
        return self.urlresolvers.reverse(
            "%s:%s" % (self.namespace, view_name),
            args=(),
            kwargs=kwargs,
            current_app=self.namespace)

# --- Views ---

def requires_app(f):
    @functools.wraps(f)
    def requirer(self, *args, **kwargs):
        if self.app is None:
            raise AttributeError("app aware views need to know"
                                 "the app")
        return f(self, *args, **kwargs)
    return requirer

class AppAwareMixin(object):
    app = None

class AppAwareTemplate(views_base.TemplateResponseMixin):
    app = None

    @requires_app
    def render_to_response(self, *args, **kwargs):
        kwargs["current_app"] = self.app.namespace

        return super(AppAwareTemplate, self).render_to_response(*args, **kwargs)

    def get_context_data(self, **kwargs):
        data = super(AppAwareTemplate, self).get_context_data(**kwargs)
        data.update({
                "base": loader.select_template(self.app.get_template_names(
                    ["base"],
                    denominator=self.get_denominator())),
                })
        return data

    @requires_app
    def get_template_names(self):
        return self.app.get_template_names(
            super(AppAwareTemplate, self).get_template_names(), 
            denominator=self.get_denominator())
    
    def get_denominator(self):
        return None

class AppAwareQuerysetMixin(object):    
    @requires_app
    def get_queryset(self):
        return self.app.queryset

    def get_slug_field():
        return "slug"

    def get_object(self, queryset=None):
        """
        Returns the object the view is displaying.

        By default this requires `self.queryset` and a `pk` or `slug` argument
        in the URLconf, but subclasses can override this to return any object.
        """
        # Use a custom queryset if provided; this is required for subclasses
        # like DateDetailView
        if queryset is None:
            queryset = self.get_queryset()

        # Next, try looking up by primary key.
        pk = self.kwargs.get('pk', None)
        slug = self.kwargs.get('slug', None)
        if pk is not None:
            queryset = queryset.filter(pk=pk)

        # Next, try looking up by slug.
        elif slug is not None:
            slug_field = self.get_slug_field()
            queryset = queryset.filter(**{slug_field: slug})

        # If none of those are defined, it's an error.
        else:
            raise AttributeError(u"Generic detail view %s must be called with "
                                 u"either an object pk or a slug."
                                 % self.__class__.__name__)

        try:
            obj = queryset.get()
        except ObjectDoesNotExist:
            raise Http404(_(u"No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})
        return obj


class AppAwareSecurityMixin(object):
    permissions = ["view"]

    @requires_app
    def dispatch(self, request, *args, **kwargs):
        is_forbidden = self.app.check_forbidden(
            request, 
            self.permissions)
        if is_forbidden:
            return is_forbidden

        return super(AppAwareSecurityMixin, self).dispatch(request, *args, **kwargs)

class AppAwareObjectSecurityMixin(AppAwareQuerysetMixin):
    permissions = ["view"]

    @requires_app
    def dispatch(self, request, *args, **kwargs):
        self.kwargs = kwargs
        obj = self.get_object()

        is_forbidden = self.app.check_forbidden(
            request, 
            self.permissions,
            obj)
        if is_forbidden:
            return is_forbidden

        return super(AppAwareObjectSecurityMixin, self).dispatch(
            request, *args, **kwargs)

# --- Models ---

class QuerySetManager(models.Manager):
    use_for_related_fields = True
    def __init__(self, qs_class=models.query.QuerySet):
        self.queryset_class = qs_class
        super(QuerySetManager, self).__init__()

    def get_query_set(self):
        return self.queryset_class(self.model)

    def __getattr__(self, attr, *args):
        try:
            return getattr(self.__class__, attr, *args)
        except AttributeError:
            return getattr(self.get_query_set(), attr, *args)

class QuerySet(models.query.QuerySet):
    """Base QuerySet class for adding custom methods that are made
    available on both the manager and subsequent cloned QuerySets"""

    @classmethod
    def as_manager(cls, ManagerClass=QuerySetManager):
        return ManagerClass(cls)

choices_placeholder = ("1", "1")
choices = lambda: [choices_placeholder]

def list_get_name(L, key):
    for i in L:
        if i.name == key:
            return i
    raise IndexError

def clear_choices(model, field_name="namespace"):
    choices = list_get_name(model._meta.fields, field_name).choices
    try:
        del choices[choices.index(choices_placeholder)]
    except ValueError:
        pass

ALL_NAMESPACES = {}

def make_registerer(model, field_name="namespace"):
    def register_app(section_tuple, app_name):
        L = list_get_name(model._meta.fields, field_name).choices
        (section_namespace, section_desc) = section_tuple
        if section_namespace not in [i for i,d in L]:
            L.append(section_tuple)
            ALL_NAMESPACES.setdefault(app_name, {})[section_namespace] = section_desc
    clear_choices(model, field_name)

    return register_app
