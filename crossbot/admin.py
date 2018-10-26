import logging

from django.db import models as django_models
from django import forms
from django.contrib import admin
from django.core.paginator import EmptyPage, InvalidPage, Paginator

import crossbot.models as models

logger = logging.getLogger(__name__)


class ItemOwnershipRecordForm(forms.ModelForm):
    item_key = forms.ChoiceField(
        choices=[(key, item.name) for key, item in models.Item.ITEMS.items()])


class ItemOwnershipRecordInline(admin.TabularInline):
    model = models.ItemOwnershipRecord
    form = ItemOwnershipRecordForm
    extra = 0


# Adapted from: https://github.com/darklow/django-suit/issues/65#issuecomment-29606850
class PaginatedInline(admin.TabularInline):
    template = 'admin/edit_inline/tabular_paginated.html'
    per_page = 20

    def get_formset(self, request, obj=None, **kwargs):
        formset_class = super(PaginatedInline, self).get_formset(
            request, obj, **kwargs)

        class PaginationFormSet(formset_class):
            def __init__(self, *args, **kwargs):
                super(PaginationFormSet, self).__init__(*args, **kwargs)

                self.query_str = self.prefix + '_page'

                qs = self.queryset
                paginator = Paginator(qs, self.per_page)
                try:
                    page_num = int(request.GET.get(self.query_str, '1'))
                except ValueError:
                    page_num = 0

                try:
                    page = paginator.get_page(page_num)
                except (EmptyPage, InvalidPage):
                    page = paginator.get_page(paginator.num_pages)

                self.items = page
                self._queryset = page.object_list

        PaginationFormSet.per_page = self.per_page
        return PaginationFormSet


class MiniCrosswordTimeInline(PaginatedInline):
    model = models.MiniCrosswordTime
    extra = 0
    ordering = ['-date']
    readonly_fields = ['timestamp']
    per_page = 10


class CrosswordTimeInline(PaginatedInline):
    model = models.CrosswordTime
    extra = 0
    ordering = ['-date']
    readonly_fields = ['timestamp']
    per_page = 10


class EasySudokuTimeInline(PaginatedInline):
    model = models.EasySudokuTime
    extra = 0
    ordering = ['-date']
    readonly_fields = ['timestamp']
    per_page = 10


@admin.register(models.CBUser)
class CBUserAdmin(admin.ModelAdmin):
    list_display = (
        '__str__',
        'crossbucks',
    )
    inlines = [
        ItemOwnershipRecordInline,
        MiniCrosswordTimeInline,
        CrosswordTimeInline,
        EasySudokuTimeInline,
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


class IsFailFilter(admin.SimpleListFilter):
    title = 'puzzle failed'
    parameter_name = 'is_fail'

    def lookups(self, request, model_admin):
        return (
            ('true', 'True'),
            ('false', 'False'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(seconds__lt=0)
        if self.value() == 'false':
            return queryset.filter(seconds__gte=0)


class _CommonTimeAdminTemplate(admin.ModelAdmin):
    # allow admins to see but not edit the timestamp
    readonly_fields = ['timestamp']
    list_display = (
        'user',
        'date',
        'seconds',
    )
    list_filter = (IsFailFilter, )


register_all_subclass_models(
    base_class=models.CommonTime, template=_CommonTimeAdminTemplate)

admin.site.register(models.QueryShorthand)
