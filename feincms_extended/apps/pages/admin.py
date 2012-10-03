from django.contrib import admin
from django.contrib import messages
from django.conf import settings as django_settings
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.forms.util import ErrorList
from django.http import HttpResponse

from feincms.module.page.models import Page, PageAdmin as PageAdminOld
from feincms.module.page.forms import PageAdminForm as PageAdminFormOld

from pages.exceptions import UniqueTemplateException
from pages.exceptions import FirstLevelOnlyTemplateException
from pages.exceptions import NoChildrenTemplateException


def check_template(model, template, instance=None, parent=None):
    def get_parent(parent):
        if not parent:
            return None
        if isinstance(parent, Page):
            return parent
        return Page.objects.get(id=parent)

    if template.unique and model.objects.filter(
                                template_key=template.key
                            ).exclude(id=instance.id if instance else -1).count():
        raise UniqueTemplateException()

    parent_page = get_parent(parent)
    if template.first_level_only and parent_page:
        raise FirstLevelOnlyTemplateException()

    if parent_page and model._feincms_templates[parent_page.template_key].no_children:
        raise NoChildrenTemplateException()

    if instance and template.no_children and instance.children.count():
        raise NoChildrenTemplateException()


def is_template_valid(model, template, instance=None, parent=None):
    try:
        check_template(model, template, instance=instance, parent=parent)
        return True
    except (
            UniqueTemplateException, FirstLevelOnlyTemplateException, 
            NoChildrenTemplateException
        ):
        pass

    return False


class PageAdminForm(PageAdminFormOld):
    def __init__(self, *args, **kwargs):
        super(PageAdminForm, self).__init__(*args, **kwargs)

        instance = kwargs.get('instance')
        parent = kwargs.get('initial', {}).get('parent')
        if not parent and instance:
            parent = instance.parent
        templates = self.get_valid_templates(instance, parent)

        choices = []
        for key, template in templates.items():
            if template.preview_image:
                choices.append((template.key,
                    mark_safe(u'<img src="%s" alt="%s" /> %s' % (
                        template.preview_image, template.key, template.title))))
            else:
                choices.append((template.key, template.title))

        self.fields['template_key'].choices = choices
        if choices:
            self.fields['template_key'].default = choices[0][0]

    def clean(self):
        cleaned_data = super(PageAdminForm, self).clean()

        # No need to think further, let the user correct errors first
        if self._errors:
            return cleaned_data

        parent = cleaned_data.get('parent')
        if parent:
            template_key = cleaned_data['template_key']
            template = self.Meta.model._feincms_templates[template_key]

            try:
                check_template(
                    self.Meta.model, template, instance=self.instance, parent=parent
                )
            except UniqueTemplateException:
                self._errors['parent'] = ErrorList(
                    [_('Template already used somewhere else.')]
                )
                del cleaned_data['parent']
            except FirstLevelOnlyTemplateException:
                self._errors['parent'] = ErrorList(
                    [_("This template can't be used as a subpage")]
                )
                del cleaned_data['parent']
            except NoChildrenTemplateException:
                self._errors['parent'] = ErrorList(
                    [_("This parent page can't have subpages")]
                )
                del cleaned_data['parent']
        return cleaned_data

    def get_valid_templates(self, instance=None, parent=None):
        """
            @return dict: dict containing all the templates valid for this instance
                (excluding unique ones already used etc.)
        """
        templates = self.Meta.model._feincms_templates.copy()

        return dict(
            filter(
                lambda (key, template): is_template_valid(
                    self.Meta.model, template, instance=instance, parent=parent
                ), templates.items()
            )
        )


class PageAdmin(PageAdminOld):
    form = PageAdminForm

    def _move_node(self, request):
        cut_item = self.model._tree_manager.get(pk=request.POST.get('cut_item'))
        pasted_on = self.model._tree_manager.get(pk=request.POST.get('pasted_on'))
        position = request.POST.get('position')

        if position == 'last-child':
            cut_item_template = self.model._feincms_templates[cut_item.template_key]
            pasted_on_template = self.model._feincms_templates[pasted_on.template_key]

            try:
                check_template(
                    self.model, cut_item_template, instance=cut_item, parent=pasted_on
                )
            except FirstLevelOnlyTemplateException:
                msg = unicode(_(u"This page can't be used as subpage."))
                messages.error(request, msg)
                return HttpResponse(msg)
            except:
                msg = unicode(_(u"Server Error."))
                messages.error(request, msg)
                return HttpResponse(msg)

        return super(PageAdmin, self)._move_node(request)

    def _actions_column(self, page):
        actions = super(PageAdmin, self)._actions_column(page)

        template = self.model._feincms_templates.get(page.template_key)
        no_children = template and template.no_children

        if no_children and getattr(page, 'feincms_editable', True):
            actions[1] = u'<img src="%spages/img/actions_placeholder.gif">' % django_settings.STATIC_URL
        return actions


# We have to unregister it, and then reregister
admin.site.unregister(Page)
admin.site.register(Page, PageAdmin)