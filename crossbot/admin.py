import logging

from django.contrib import admin
from django import forms

import crossbot.models as models

logger = logging.getLogger(__name__)


class ItemOwnershipRecordForm(forms.ModelForm):
    item_key = forms.ChoiceField(
        choices=[(key, item.name) for key, item in models.Item.ITEMS.items()])


class ItemOwnershipRecordInline(admin.TabularInline):
    model = models.ItemOwnershipRecord
    form = ItemOwnershipRecordForm
    extra = 0


@admin.register(models.CBUser)
class CBUserAdmin(admin.ModelAdmin):
    inlines = [
        ItemOwnershipRecordInline,
    ]


# TODO: this is unnecessary, just use the @register decorator w/ multiple args


# inspired by https://lukedrummond.net/2014/02/abstract-models-and-the-django-admin/
def mk_from_template(template, clsname, base):

    class_meta = type('Meta', (object, ), {'model': base})
    class_dict = {'Meta': class_meta}

    #use type to create the class
    model_admin = type(base.__name__ + 'ModelAdmin', (template, ), class_dict)

    return model_admin


def register_all_subclass_models(base_class, template):
    for c in base_class.__subclasses__():
        a = mk_from_template(template, c.__name__, base_class)
        logger.debug("registering model %s %s" % (c, a))
        admin.site.register(c, a)


class _CommonTimeAdminTemplate(admin.ModelAdmin):
    # allow admins to see but not edit the timestamp
    readonly_fields = ['timestamp']


register_all_subclass_models(
    base_class=models.CommonTime, template=_CommonTimeAdminTemplate)

admin.site.register(models.QueryShorthand)
