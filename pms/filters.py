"""
Module: filters.py

This module contains custom Django filters and filter sets for 
the PMS (Performance Management System) app.
"""

import datetime
import django_filters
from django import forms
from django_filters import DateFilter
from pms.models import EmployeeKeyResult, EmployeeObjective, Feedback, KeyResult, Objective
from base.methods import reload_queryset
from base.filters import FilterSet


class DateRangeFilter(django_filters.Filter):
    """
    A custom Django filter for filtering querysets based on date ranges.

    This filter allows you to filter a queryset based on date ranges such as 'today',
    'yesterday', 'week', or 'month' in the 'created_at' field of model.
    """

    def filter(self, qs, value):
        if value:
            if value == "today":
                today = datetime.date.today()
                qs = qs.filter(created_at=today)
            if value == "yesterday":
                today = datetime.date.today()
                yesterday = today - datetime.timedelta(days=1)
                qs = qs.filter(created_at=yesterday)
            if value == "week":
                today = datetime.date.today()
                start_of_week = today - datetime.timedelta(days=today.weekday())
                end_of_week = start_of_week + datetime.timedelta(days=6)
                qs = qs.filter(created_at__range=[start_of_week, end_of_week])
            elif value == "month":
                today = datetime.date.today()
                start_of_month = datetime.date(today.year, today.month, 1)
                end_of_month = start_of_month + datetime.timedelta(days=31)
                qs = qs.filter(created_at__range=[start_of_month, end_of_month])
        return qs


class CustomFilterSet(django_filters.FilterSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.form.fields)
        for field_name, field in self.form.fields.items():
            filter_widget = self.filters[field_name]
            widget = filter_widget.field.widget
            if isinstance(
                widget, (forms.NumberInput, forms.EmailInput, forms.TextInput)
            ):
                field.widget.attrs.update({"class": "oh-input w-100"})
            elif isinstance(widget, (forms.Select,)):
                field.widget.attrs.update(
                    {
                        "class": "oh-select oh-select-2 select2-hidden-accessible",
                    }
                )
            elif isinstance(widget, (forms.Textarea)):
                field.widget.attrs.update({"class": "oh-input w-100"})
            elif isinstance(
                widget,
                (
                    forms.CheckboxInput,
                    forms.CheckboxSelectMultiple,
                ),
            ):
                field.widget.attrs.update({"class": "oh-switch__checkbox"})
            elif isinstance(widget, (forms.ModelChoiceField)):
                field.widget.attrs.update(
                    {
                        "class": "oh-select oh-select-2 select2-hidden-accessible",
                    }
                )
            if isinstance(field, django_filters.CharFilter):
                field.lookup_expr = "icontains"


class ActualObjectiveFilter(FilterSet):
    """
    ActualObjectiveFilter
    """

    search = django_filters.CharFilter(method="search_method")

    class Meta:
        model = Objective
        fields = [
            "managers",
            "assignees",
            "duration",
            "employee_objective",
            "employee_objective__key_result_id",
            "employee_objective__progress_percentage",
        ]

    def search_method(self, queryset, _, value: str):
        """
        This method is used to search employees and objective
        """
        values = value.split(" ")
        empty = queryset.model.objects.none()
        for split in values:
            empty = empty | (
                queryset.filter(managers__employee_first_name__icontains=split)
                | queryset.filter(managers__employee_last_name__icontains=split)
                | queryset.filter(assignees__employee_first_name__icontains=split)
                | queryset.filter(assignees__employee_last_name__icontains=split)
                | queryset.filter(title__icontains=split)
            )

        return empty.distinct()


class ObjectiveFilter(CustomFilterSet):
    """
    Custom filter set for EmployeeObjective records.

    This filter set allows to filter EmployeeObjective records based on various criteria.
    """

    employee_objective = django_filters.CharFilter(field_name="id")
    employee_objective__key_result_id = django_filters.CharFilter(
        field_name="key_result_id"
    )
    employee_objective__progress_percentage = django_filters.CharFilter(
        field_name="progress_percentage"
    )
    managers = django_filters.CharFilter(field_name="objective_id__managers")
    search = django_filters.CharFilter(method="search_method")
    created_at_date_range = DateRangeFilter(field_name="created_at")
    created_at = DateFilter(
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input  w-100"}),
        # add lookup expression here
    )
    updated_at = DateFilter(
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input  w-100"}),
        # add lookup expression here
    )
    start_date = DateFilter(
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input  w-100"}),
        # add lookup expression here
    )
    end_date = DateFilter(
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input  w-100"}),
        # add lookup expression here
    )

    class Meta:
        """
        A nested class that specifies the model and fields for the filter.
        """

        model = EmployeeObjective
        fields = [
            "objective",
            "status",
            "employee_id",
            "created_at",
            "start_date",
            "updated_at",
            "end_date",
            "archive",
            "objective_id",
        ]

    def search_method(self, queryset, _, value: str):
        """
        This method is used to search in managers and objective
        """
        values = value.split(" ")
        empty = queryset.model.objects.none()
        for split in values:
            empty = empty | (
                queryset.filter(objective_id__title=split)
                | queryset.filter(
                    objective_id__managers__employee_first_name__icontains=split
                )
                | queryset.filter(
                    objective_id__managers__employee_last_name__icontains=split
                )
            )
        return empty


class FeedbackFilter(CustomFilterSet):
    """
    Custom filter set for Feedback records.

    This filter set allows to filter Feedback records based on various criteria.
    """

    review_cycle = django_filters.CharFilter(lookup_expr="icontains")
    created_at_date_range = DateRangeFilter(field_name="created_at")
    start_date = DateFilter(
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input  w-100"}),
        # add lookup expression here
    )
    end_date = DateFilter(
        widget=forms.DateInput(attrs={"type": "date", "class": "oh-input  w-100"}),
        # add lookup expression here
    )

    class Meta:
        """
        A nested class that specifies the model and fields for the filter.
        """

        model = Feedback
        fields = "__all__"

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super(FeedbackFilter, self).__init__(
            data=data, queryset=queryset, request=request, prefix=prefix
        )


class KeyResultFilter(CustomFilterSet):

    class Meta:
        model = EmployeeKeyResult
        fields = "__all__"

class ActualKeyResultFilter(FilterSet):
    """
    Filter through KeyResult model
    """

    search = django_filters.CharFilter(method="search_method")

    class Meta:
        model = KeyResult
        fields = [
            "progress_type",
            "target_value",
            "duration",
            'company_id'
        ]

    def search_method(self, queryset, _, value: str):
        """
        This method is used to search employees and objective
        """
        values = value.split(" ")
        empty = queryset.model.objects.none()
        for split in values:
            empty = empty | (queryset.filter(title__icontains=split)
            )

        return empty.distinct()


class ObjectiveReGroup:
    """
    Class to keep the field name for group by option
    """

    fields = [
        ("", "select"),
        ("employee_id", "Owner"),
        ("status", "Status"),
    ]
