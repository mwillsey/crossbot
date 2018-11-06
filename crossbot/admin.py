import logging

from django.db import models as django_models
from django import forms
from django.contrib import admin
from django.core.paginator import EmptyPage, InvalidPage, Paginator

from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter

import crossbot.models as models

logger = logging.getLogger(__name__)


class ItemOwnershipRecordForm(forms.ModelForm):
    item_key = forms.ChoiceField(
        choices=[(key, item.name) for key, item in models.Item.ITEMS.items()]
    )


class ItemOwnershipRecordInline(admin.TabularInline):
    model = models.ItemOwnershipRecord
    form = ItemOwnershipRecordForm
    extra = 0

class UserSkillInline(admin.StackedInline):
    model = models.PredictionUser
    extra = 0

# Adapted from: https://github.com/darklow/django-suit/issues/65#issuecomment-29606850
class PaginatedInline(admin.TabularInline):
    template = 'admin/edit_inline/tabular_paginated.html'
    per_page = 10

    def get_formset(self, request, obj=None, **kwargs):
        formset_class = super(PaginatedInline,
                              self).get_formset(request, obj, **kwargs)

        class PaginationFormSet(formset_class):
            def __init__(self, *args, **kwargs):
                super(PaginationFormSet, self).__init__(*args, **kwargs)

                self.query_str = self.prefix + '_page'

                paginator = Paginator(self.queryset, self.per_page)
                try:
                    page_num = int(request.GET.get(self.query_str, '1'))
                except ValueError:
                    page_num = 0

                try:
                    page = paginator.get_page(page_num)
                except (EmptyPage, InvalidPage):
                    page = paginator.get_page(paginator.num_pages)

                self.items = page

            def get_queryset(self):
                return self.items.object_list

        PaginationFormSet.per_page = self.per_page
        return PaginationFormSet


class CommonTimeInline(PaginatedInline):
    extra = 0
    ordering = ['-date']
    readonly_fields = ['timestamp']


class MiniCrosswordTimeInline(CommonTimeInline):
    model = models.MiniCrosswordTime


class CrosswordTimeInline(CommonTimeInline):
    model = models.CrosswordTime


class EasySudokuTimeInline(CommonTimeInline):
    model = models.EasySudokuTime


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
        UserSkillInline,
    ]


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


@admin.register(
    models.MiniCrosswordTime, models.CrosswordTime, models.EasySudokuTime
)
class CommonTimeAdminTemplate(admin.ModelAdmin):
    # allow admins to see but not edit the timestamp
    readonly_fields = ['timestamp']
    list_display = (
        'user',
        'date',
        'seconds',
    )
    list_filter = (IsFailFilter, )


admin.site.register(models.QueryShorthand)


@admin.register(models.Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'date',
        'prediction',
        'residual',
    )
    list_filter = ('date', ('user', RelatedDropdownFilter))


@admin.register(models.PredictionUser)
class PredictionUserAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'skill',
        'skill_25',
        'skill_75',
    )


@admin.register(models.PredictionDate)
class PredictionDateAdmin(admin.ModelAdmin):
    list_display = (
        'date',
        'difficulty',
        'difficulty_25',
        'difficulty_75',
    )
    list_filter = ('date', )


admin.site.register(models.PredictionParameter)
