from django.contrib import admin
from django.conf import settings as django_settings
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.forms.util import ErrorList
from django.http import HttpResponse

from feincms.module.page.models import Page, PageAdmin as PageAdminOld
from feincms.module.page.forms import PageAdminForm as PageAdminFormOld

from pages.exceptions import UniqueTemplateException


def check_template(model, template, instance=None, parent=None):
    if template.unique and model.objects.filter(
                                template_key=template.key
                            ).exclude(id=instance.id if instance else -1).count():
        raise UniqueTemplateException()


def is_template_valid(model, template, instance=None, parent=None):
    try:
        check_template(model, template, instance=instance, parent=parent)
        return True
    except UniqueTemplateException:
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
                choices.append(
                    (template.key, mark_safe(
                        u'<img src="%s" alt="%s" /> %s' % (
                            template.preview_image, template.key, template.title
                        )
                    ))
                )
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

# We have to unregister the default configuration, and register ours
admin.site.unregister(Page)
admin.site.register(Page, PageAdmin)