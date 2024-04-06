"""
forms.py

This module is used to register forms for base module
"""

import calendar
import os
from typing import Any
import uuid
import datetime
from datetime import date, timedelta
from django.contrib.auth import authenticate
from django import forms
from django.contrib.auth.models import Group, Permission, User
from django.forms import DateInput, HiddenInput, TextInput
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _trans
from django.template.loader import render_to_string
from base import thread_local_middleware
from employee.filters import EmployeeFilter
from employee.models import Employee, EmployeeTag
from base.models import (
    Announcement,
    AnnouncementComment,
    AnnouncementExpire,
    Attachment,
    BaserequestFile,
    Company,
    Department,
    DriverViewed,
    DynamicEmailConfiguration,
    DynamicPagination,
    JobPosition,
    JobRole,
    MultipleApprovalCondition,
    ShiftRequestComment,
    WorkType,
    EmployeeType,
    EmployeeShift,
    EmployeeShiftSchedule,
    RotatingShift,
    RotatingShiftAssign,
    RotatingWorkType,
    RotatingWorkTypeAssign,
    WorkTypeRequest,
    ShiftRequest,
    EmployeeShiftDay,
    Tags,
    WorkTypeRequestComment,
)
from base.methods import reload_queryset
from horilla_audit.models import AuditTag
from horilla_widgets.widgets.horilla_multi_select_field import HorillaMultiSelectField
from horilla_widgets.widgets.select_widgets import HorillaMultiSelectWidget
from employee.forms import MultipleFileField


# your form here


def validate_time_format(value):
    """
    this method is used to validate the format of duration like fields.
    """
    if len(value) > 6:
        raise ValidationError(_("Invalid format, it should be HH:MM format"))
    try:
        hour, minute = value.split(":")
        hour = int(hour)
        minute = int(minute)
        if len(str(hour)) > 3 or minute not in range(60):
            raise ValidationError(_("Invalid format, it should be HH:MM format"))
    except ValueError as error:
        raise ValidationError(_("Invalid format, it should be HH:MM format")) from error


BASED_ON = [
    ("after", _trans("After")),
    ("weekly", _trans("Weekend")),
    ("monthly", _trans("Monthly")),
]


def get_next_week_date(target_day, start_date):
    """
    Calculates the date of the next occurrence of the target day within the next week.

    Parameters:
        target_day (int): The target day of the week (0-6, where Monday is 0 and Sunday is 6).
        start_date (datetime.date): The starting date.

    Returns:
        datetime.date: The date of the next occurrence of the target day within the next week.
    """
    if start_date.weekday() == target_day:
        return start_date
    days_until_target_day = (target_day - start_date.weekday()) % 7
    if days_until_target_day == 0:
        days_until_target_day = 7
    return start_date + timedelta(days=days_until_target_day)


def get_next_monthly_date(start_date, rotate_every):
    """
    Given a start date and a rotation day (specified as an integer between 1 and 31, or
    the string 'last'),calculates the next rotation date for a monthly rotation schedule.

    If the rotation day has not yet occurred in the current month, the next rotation date
    will be on the rotation day of the current month. If the rotation day has already
    occurred in the current month, the next rotation date will be on the rotation day of
    the next month.

    If 'last' is specified as the rotation day, the next rotation date will be on the
    last day of the current month.

    Parameters:
    - start_date: The start date of the rotation schedule, as a datetime.date object.
    - rotate_every: The rotation day, specified as an integer between 1 and 31, or the
      string 'last'.

    Returns:
    - A datetime.date object representing the next rotation date.
    """

    if rotate_every == "last":
        # Set rotate_every to the last day of the current month
        last_day = calendar.monthrange(start_date.year, start_date.month)[1]
        rotate_every = str(last_day)
    rotate_every = int(rotate_every)

    # Calculate the next change date
    if start_date.day <= rotate_every or rotate_every == 0:
        # If the rotation day has not occurred yet this month, or if it's the last-
        # day of the month, set the next change date to the rotation day of this month
        try:
            next_change = datetime.date(start_date.year, start_date.month, rotate_every)
        except ValueError:
            next_change = datetime.date(
                start_date.year, start_date.month + 1, 1
            )  # Advance to next month
            # Set day to rotate_every
            next_change = datetime.date(
                next_change.year, next_change.month, rotate_every
            )
    else:
        # If the rotation day has already occurred this month, set the next change
        # date to the rotation day of the next month
        last_day = calendar.monthrange(start_date.year, start_date.month)[1]
        next_month_start = start_date.replace(day=last_day) + timedelta(days=1)
        try:
            next_change = next_month_start.replace(day=rotate_every)
        except ValueError:
            next_change = (
                next_month_start.replace(month=next_month_start.month + 1)
                + timedelta(days=1)
            ).replace(day=rotate_every)

    return next_change


class ModelForm(forms.ModelForm):
    """
    Override django model's form to add initial styling
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        request = getattr(thread_local_middleware._thread_locals, "request", None)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.DateInput)):
                field.initial = date.today()

            if isinstance(
                widget,
                (forms.NumberInput, forms.EmailInput, forms.TextInput, forms.FileInput),
            ):
                label = ""
                if field.label is not None:
                    label = _(field.label.title())
                field.widget.attrs.update(
                    {"class": "oh-input w-100", "placeholder": label}
                )
            elif isinstance(widget, (forms.Select,)):
                field.empty_label = None
                if not isinstance(field, forms.ModelMultipleChoiceField):
                    label = ""
                    if field.label is not None:
                        label = _(field.label)
                    field.empty_label = _("---Choose {label}---").format(label=label)
                field.widget.attrs.update(
                    {"class": "oh-select oh-select-2 select2-hidden-accessible"}
                )
            elif isinstance(widget, (forms.Textarea)):
                field.widget.attrs.update(
                    {
                        "class": "oh-input w-100",
                        "placeholder": _(field.label),
                        "rows": 2,
                        "cols": 40,
                    }
                )
            elif isinstance(
                widget,
                (
                    forms.CheckboxInput,
                    forms.CheckboxSelectMultiple,
                ),
            ):
                field.widget.attrs.update({"class": "oh-switch__checkbox"})

            try:
                self.fields["employee_id"].initial = request.user.employee_get
            except:
                pass

            try:
                self.fields["company_id"].initial = (
                    request.user.employee_get.get_company
                )
            except:
                pass


class Form(forms.Form):
    """
    Overrides to add initial styling to the django Form instance
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(
                widget, (forms.NumberInput, forms.EmailInput, forms.TextInput)
            ):
                if field.label is not None:
                    label = _(field.label)
                    field.widget.attrs.update(
                        {"class": "oh-input w-100", "placeholder": label}
                    )
            elif isinstance(widget, (forms.Select,)):
                label = ""
                if field.label is not None:
                    label = field.label.replace("id", " ")
                field.empty_label = _("---Choose {label}---").format(label=label)
                field.widget.attrs.update(
                    {"class": "oh-select oh-select-2 select2-hidden-accessible"}
                )
            elif isinstance(widget, (forms.Textarea)):
                label = _(field.label)
                field.widget.attrs.update(
                    {
                        "class": "oh-input w-100",
                        "placeholder": label,
                        "rows": 2,
                        "cols": 40,
                    }
                )
            elif isinstance(
                widget,
                (
                    forms.CheckboxInput,
                    forms.CheckboxSelectMultiple,
                ),
            ):
                field.widget.attrs.update({"class": "oh-switch__checkbox"})


class UserGroupForm(ModelForm):
    """
    Django user groups form
    """

    try:
        permissions = forms.MultipleChoiceField(
            choices=[(perm.codename, perm.name) for perm in Permission.objects.all()],
            error_messages={
                "required": "Please choose a permission.",
            },
        )
    except:
        pass

    class Meta:
        """
        Meta class for additional options
        """

        model = Group
        fields = ["name", "permissions"]

    def save(self, commit=True):
        """
        ModelForm save override
        """
        group = super().save(commit=False)
        if self.instance:
            group = self.instance
        group.save()

        # Convert the selected codenames back to Permission instances
        permissions_codenames = self.cleaned_data["permissions"]
        permissions = Permission.objects.filter(codename__in=permissions_codenames)

        # Set the associated permissions
        group.permissions.set(permissions)

        if commit:
            group.save()

        return group


class AssignUserGroup(Form):
    """
    Form to assign groups
    """

    employee = forms.ModelMultipleChoiceField(
        queryset=Employee.objects.all(), required=False
    )
    group = forms.ModelChoiceField(queryset=Group.objects.all())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)

    def save(self):
        """
        Save method to assign group to employees
        """
        employees = self.cleaned_data["employee"]
        group = self.cleaned_data["group"]
        group.user_set.clear()
        for employee in employees:
            employee.employee_user_id.groups.add(group)
        return group


class AssignPermission(Form):
    """
    Forms to assign user permision
    """

    employee = HorillaMultiSelectField(
        queryset=Employee.objects.all(),
        widget=HorillaMultiSelectWidget(
            filter_route_name="employee-widget-filter",
            filter_class=EmployeeFilter,
            filter_instance_contex_name="f",
            filter_template_path="employee_filters.html",
            required=True,
        ),
        label="Employee",
    )
    try:
        permissions = forms.MultipleChoiceField(
            choices=[(perm.codename, perm.name) for perm in Permission.objects.all()],
            error_messages={
                "required": "Please choose a permission.",
            },
        )
    except:
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)

    def clean(self):
        emps = self.data.getlist("employee")
        if emps:
            self.errors.pop("employee", None)
        super().clean()
        return

    def save(self):
        """
        Save method to assign permission to employee
        """
        user_ids = Employee.objects.filter(
            id__in=self.data.getlist("employee")
        ).values_list("employee_user_id", flat=True)
        permissions = self.cleaned_data["permissions"]
        permissions = Permission.objects.filter(codename__in=permissions)
        users = User.objects.filter(id__in=user_ids)
        for user in users:
            user.user_permissions.set(permissions)

        return self


class CompanyForm(ModelForm):
    """
    Company model's form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = Company
        fields = "__all__"
        excluded_fields = ["date_format", "time_format"]

    def validate_image(self, file):
        max_size = 5 * 1024 * 1024

        if file.size > max_size:
            raise ValidationError("File size should be less than 5MB.")

        # Check file extension
        valid_extensions = [".jpg", ".jpeg", ".png", ".webp", ".svg"]
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in valid_extensions:
            raise ValidationError("Unsupported file extension.")

    def clean_icon(self):
        icon = self.cleaned_data.get("icon")
        if icon:
            self.validate_image(icon)
        return icon


class DepartmentForm(ModelForm):
    """
    Department model's form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = Department
        fields = "__all__"
        exclude = ["is_active"]


class JobPositionForm(ModelForm):
    """
    JobPosition model's form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = JobPosition
        fields = "__all__"
        exclude = ["is_active"]


class JobRoleForm(ModelForm):
    """
    JobRole model's form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = JobRole
        fields = "__all__"
        exclude = ["is_active"]


class WorkTypeForm(ModelForm):
    """
    WorkType model's form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = WorkType
        fields = "__all__"
        exclude = ["is_active"]


class RotatingWorkTypeForm(ModelForm):
    """
    RotatingWorkType model's form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = RotatingWorkType
        fields = "__all__"
        exclude = ["employee_id", "is_active"]
        widgets = {
            "start_date": DateInput(attrs={"type": "date"}),
        }


class RotatingWorkTypeAssignForm(ModelForm):
    """
    RotatingWorkTypeAssign model's form
    """

    employee_id = HorillaMultiSelectField(
        queryset=Employee.objects.filter(employee_work_info__isnull=False),
        widget=HorillaMultiSelectWidget(
            filter_route_name="employee-widget-filter",
            filter_class=EmployeeFilter,
            filter_instance_contex_name="f",
            filter_template_path="employee_filters.html",
        ),
        label=_trans("Employees"),
    )
    based_on = forms.ChoiceField(
        choices=BASED_ON, initial="daily", label=_trans("Based on")
    )
    rotate_after_day = forms.IntegerField(initial=5, label=_trans("Rotate after day"))
    start_date = forms.DateField(
        initial=datetime.date.today, widget=forms.DateInput, label=_trans("Start date")
    )

    class Meta:
        """
        Meta class for additional options
        """

        model = RotatingWorkTypeAssign
        fields = "__all__"
        exclude = [
            "next_change_date",
            "current_work_type",
            "next_work_type",
            "is_active",
        ]
        widgets = {
            "start_date": DateInput(attrs={"type": "date"}),
            "is_active": HiddenInput(),
        }
        labels = {
            "is_active": _trans("Is Active"),
            "rotate_every_weekend": _trans("Rotate every weekend"),
            "rotate_every": _trans("Rotate every"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        self.fields["rotate_every_weekend"].widget.attrs.update(
            {
                "class": "w-100",
                "style": "display:none; height:50px; border-radius:0;border:1px \
                    solid hsl(213deg,22%,84%);",
                "data-hidden": True,
            }
        )
        self.fields["rotate_every"].widget.attrs.update(
            {
                "class": "w-100",
                "style": "display:none; height:50px; border-radius:0;border:1px \
                    solid hsl(213deg,22%,84%);",
                "data-hidden": True,
            }
        )
        self.fields["rotate_after_day"].widget.attrs.update(
            {
                "class": "w-100 oh-input",
                "style": " height:50px; border-radius:0;",
            }
        )
        self.fields["based_on"].widget.attrs.update(
            {
                "class": "w-100",
                "style": " height:50px; border-radius:0;border:1px solid hsl(213deg,22%,84%);",
            }
        )
        self.fields["start_date"].widget = forms.DateInput(
            attrs={
                "class": "w-100 oh-input",
                "type": "date",
                "style": " height:50px; border-radius:0;",
            }
        )
        self.fields["rotating_work_type_id"].widget.attrs.update(
            {
                "class": "oh-select oh-select-2",
            }
        )
        self.fields["employee_id"].widget.attrs.update(
            {
                "class": "oh-select oh-select-2",
            }
        )

    def clean_employee_id(self):
        employee_ids = self.cleaned_data.get("employee_id")
        if employee_ids:
            return employee_ids[0]
        else:
            return ValidationError(_("This field is required"))

    def clean(self):
        super().clean()
        self.instance.employee_id = Employee.objects.filter(
            id=self.data.get("employee_id")
        ).first()

        self.errors.pop("employee_id", None)
        if self.instance.employee_id is None:
            raise ValidationError({"employee_id": _("This field is required")})
        super().clean()
        cleaned_data = super().clean()
        if "rotate_after_day" in self.errors:
            del self.errors["rotate_after_day"]
        return cleaned_data

    def save(self, commit=False, manager=None):
        employee_ids = self.data.getlist("employee_id")
        rotating_work_type = RotatingWorkType.objects.get(
            id=self.data["rotating_work_type_id"]
        )

        day_name = self.cleaned_data["rotate_every_weekend"]
        day_names = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        target_day = day_names.index(day_name.lower())

        for employee_id in employee_ids:
            employee = Employee.objects.filter(id=employee_id).first()
            rotating_work_type_assign = RotatingWorkTypeAssign()
            rotating_work_type_assign.rotating_work_type_id = rotating_work_type
            rotating_work_type_assign.employee_id = employee
            rotating_work_type_assign.based_on = self.cleaned_data["based_on"]
            rotating_work_type_assign.start_date = self.cleaned_data["start_date"]
            rotating_work_type_assign.next_change_date = self.cleaned_data["start_date"]
            rotating_work_type_assign.rotate_after_day = self.data.get(
                "rotate_after_day"
            )
            rotating_work_type_assign.rotate_every = self.cleaned_data["rotate_every"]
            rotating_work_type_assign.rotate_every_weekend = self.cleaned_data[
                "rotate_every_weekend"
            ]
            rotating_work_type_assign.next_change_date = self.cleaned_data["start_date"]
            rotating_work_type_assign.current_work_type = (
                employee.employee_work_info.work_type_id
            )
            rotating_work_type_assign.next_work_type = rotating_work_type.work_type2
            based_on = self.cleaned_data["based_on"]
            start_date = self.cleaned_data["start_date"]
            if based_on == "weekly":
                next_date = get_next_week_date(target_day, start_date)
                rotating_work_type_assign.next_change_date = next_date
            elif based_on == "monthly":
                # 0, 1, 2, ..., 31, or "last"
                rotate_every = self.cleaned_data["rotate_every"]
                start_date = self.cleaned_data["start_date"]
                next_date = get_next_monthly_date(start_date, rotate_every)
                rotating_work_type_assign.next_change_date = next_date
            elif based_on == "after":
                rotating_work_type_assign.next_change_date = (
                    rotating_work_type_assign.start_date
                    + datetime.timedelta(days=int(self.data.get("rotate_after_day")))
                )

            rotating_work_type_assign.save()


class RotatingWorkTypeAssignUpdateForm(forms.ModelForm):
    """
    RotatingWorkTypeAssign model's form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = RotatingWorkTypeAssign
        fields = "__all__"
        exclude = [
            "next_change_date",
            "current_work_type",
            "next_work_type",
            "is_active",
        ]
        widgets = {
            "start_date": DateInput(attrs={"type": "date"}),
        }
        labels = {
            "start_date": _trans("Start date"),
            "rotate_after_day": _trans("Rotate after day"),
            "rotate_every_weekend": _trans("Rotate every weekend"),
            "rotate_every": _trans("Rotate every"),
            "based_on": _trans("Based on"),
            "is_active": _trans("Is Active"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)

        self.fields["rotate_every_weekend"].widget.attrs.update(
            {
                "class": "w-100",
                "style": "display:none; height:50px; border-radius:0;border:1px\
                    solid hsl(213deg,22%,84%);",
                "data-hidden": True,
            }
        )
        self.fields["rotate_every"].widget.attrs.update(
            {
                "class": "w-100",
                "style": "display:none; height:50px; border-radius:0;border:1px \
                    solid hsl(213deg,22%,84%);",
                "data-hidden": True,
            }
        )
        self.fields["rotate_after_day"].widget.attrs.update(
            {
                "class": "w-100 oh-input",
                "style": " height:50px; border-radius:0;",
            }
        )
        self.fields["based_on"].widget.attrs.update(
            {
                "class": "w-100",
                "style": " height:50px; border-radius:0; border:1px solid \
                    hsl(213deg,22%,84%);",
            }
        )
        self.fields["start_date"].widget = forms.DateInput(
            attrs={
                "class": "w-100 oh-input",
                "type": "date",
                "style": " height:50px; border-radius:0;",
            }
        )
        self.fields["rotating_work_type_id"].widget.attrs.update(
            {
                "class": "oh-select oh-select-2",
            }
        )
        self.fields["employee_id"].widget.attrs.update(
            {
                "class": "oh-select oh-select-2",
            }
        )

    def save(self, *args, **kwargs):
        day_name = self.cleaned_data["rotate_every_weekend"]
        day_names = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        target_day = day_names.index(day_name.lower())

        based_on = self.cleaned_data["based_on"]
        start_date = self.instance.start_date
        if based_on == "weekly":
            next_date = get_next_week_date(target_day, start_date)
            self.instance.next_change_date = next_date
        elif based_on == "monthly":
            rotate_every = self.instance.rotate_every  # 0, 1, 2, ..., 31, or "last"
            start_date = self.instance.start_date
            next_date = get_next_monthly_date(start_date, rotate_every)
            self.instance.next_change_date = next_date
        elif based_on == "after":
            self.instance.next_change_date = (
                self.instance.start_date
                + datetime.timedelta(days=int(self.data.get("rotate_after_day")))
            )
        return super().save()


class EmployeeTypeForm(ModelForm):
    """
    EmployeeType form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = EmployeeType
        fields = "__all__"
        exclude = ["is_active"]


class EmployeeShiftForm(ModelForm):
    """
    EmployeeShift Form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = EmployeeShift
        fields = "__all__"
        exclude = ["days", "is_active"]

    def clean(self):
        full_time = self.data["full_time"]
        validate_time_format(full_time)
        full_time = self.data["weekly_full_time"]
        validate_time_format(full_time)
        return super().clean()


class EmployeeShiftScheduleUpdateForm(ModelForm):
    """
    EmployeeShiftSchedule model's form
    """

    class Meta:
        """
        Meta class for additional options
        """

        fields = "__all__"
        exclude = ["is_active"]
        widgets = {
            "start_time": DateInput(attrs={"type": "time"}),
            "end_time": DateInput(attrs={"type": "time"}),
        }
        model = EmployeeShiftSchedule

    def __init__(self, *args, **kwargs):
        if instance := kwargs.get("instance"):
            # """
            # django forms not showing value inside the date, time html element.
            # so here overriding default forms instance method to set initial value
            # """
            initial = {
                "start_time": instance.start_time.strftime("%H:%M"),
                "end_time": instance.end_time.strftime("%H:%M"),
            }
            kwargs["initial"] = initial
        super().__init__(*args, **kwargs)


class EmployeeShiftScheduleForm(ModelForm):
    """
    EmployeeShiftSchedule model's form
    """

    day = forms.ModelMultipleChoiceField(
        queryset=EmployeeShiftDay.objects.all(),
    )

    class Meta:
        """
        Meta class for additional options
        """

        model = EmployeeShiftSchedule
        fields = "__all__"
        exclude = ["is_night_shift", "is_active"]
        widgets = {
            "start_time": DateInput(attrs={"type": "time"}),
            "end_time": DateInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, **kwargs):
        if instance := kwargs.get("instance"):
            # """
            # django forms not showing value inside the date, time html element.
            # so here overriding default forms instance method to set initial value
            # """
            initial = {
                "start_time": instance.start_time.strftime("%H:%M"),
                "end_time": instance.end_time.strftime("%H:%M"),
            }
            kwargs["initial"] = initial
        super().__init__(*args, **kwargs)
        self.fields["day"].widget.attrs.update({"id": str(uuid.uuid4())})
        self.fields["shift_id"].widget.attrs.update({"id": str(uuid.uuid4())})

    def save(self, commit=True):
        instance = super().save(commit=False)
        for day in self.data.getlist("day"):
            if int(day) != int(instance.day.id):
                data_copy = self.data.copy()
                data_copy.update({"day": str(day)})
                shift_schedule = EmployeeShiftScheduleUpdateForm(data_copy).save(
                    commit=False
                )
                shift_schedule.save()
        if commit:
            instance.save()
        return instance

    def clean_day(self):
        """
        Validation to day field
        """
        days = self.cleaned_data["day"]
        for day in days:
            attendance = EmployeeShiftSchedule.objects.filter(
                day=day, shift_id=self.data["shift_id"]
            ).first()
            if attendance is not None:
                raise ValidationError(
                    _("Shift schedule is already exist for {day}").format(
                        day=_(day.day)
                    )
                )
        if days.first() is None:
            raise ValidationError(_("Employee not chosen"))

        return days.first()


class RotatingShiftForm(ModelForm):
    """
    RotatingShift model's form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = RotatingShift
        fields = "__all__"
        exclude = ["employee_id", "is_active"]


class RotatingShiftAssignForm(forms.ModelForm):
    """
    RotatingShiftAssign model's form
    """

    employee_id = HorillaMultiSelectField(
        queryset=Employee.objects.filter(employee_work_info__isnull=False),
        widget=HorillaMultiSelectWidget(
            filter_route_name="employee-widget-filter",
            filter_class=EmployeeFilter,
            filter_instance_contex_name="f",
            filter_template_path="employee_filters.html",
        ),
        label=_trans("Employees"),
    )
    based_on = forms.ChoiceField(
        choices=BASED_ON, initial="daily", label=_trans("Based on")
    )
    rotate_after_day = forms.IntegerField(initial=5, label=_trans("Rotate after day"))
    start_date = forms.DateField(
        initial=datetime.date.today, widget=forms.DateInput, label=_trans("Start date")
    )

    class Meta:
        """
        Meta class for additional options
        """

        model = RotatingShiftAssign
        fields = "__all__"
        exclude = ["next_change_date", "current_shift", "next_shift", "is_active"]
        widgets = {
            "start_date": DateInput(attrs={"type": "date"}),
        }
        labels = {
            "rotating_shift_id": _trans("Rotating Shift"),
            "start_date": _("Start date"),
            "is_active": _trans("Is Active"),
            "rotate_every_weekend": _trans("Rotate every weekend"),
            "rotate_every": _trans("Rotate every"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        self.fields["rotate_every_weekend"].widget.attrs.update(
            {
                "class": "w-100 ",
                "style": "display:none; height:50px; border-radius:0;border:1px \
                    solid hsl(213deg,22%,84%);",
                "data-hidden": True,
            }
        )
        self.fields["rotate_every"].widget.attrs.update(
            {
                "class": "w-100 ",
                "style": "display:none; height:50px; border-radius:0;border:1px \
                    solid hsl(213deg,22%,84%);",
                "data-hidden": True,
            }
        )
        self.fields["rotate_after_day"].widget.attrs.update(
            {
                "class": "w-100 oh-input",
                "style": " height:50px; border-radius:0;",
            }
        )
        self.fields["based_on"].widget.attrs.update(
            {
                "class": "w-100",
                "style": " height:50px; border-radius:0;border:1px solid hsl(213deg,22%,84%);",
            }
        )
        self.fields["start_date"].widget = forms.DateInput(
            attrs={
                "class": "w-100 oh-input",
                "type": "date",
                "style": " height:50px; border-radius:0;",
            }
        )
        self.fields["rotating_shift_id"].widget.attrs.update(
            {
                "class": "oh-select oh-select-2",
            }
        )
        self.fields["employee_id"].widget.attrs.update(
            {
                "class": "oh-select oh-select-2",
            }
        )

    def clean_employee_id(self):
        """
        Validation to employee_id field
        """
        employee_ids = self.cleaned_data.get("employee_id")
        if employee_ids:
            return employee_ids[0]
        else:
            return ValidationError(_("This field is required"))

    def clean(self):
        super().clean()
        self.instance.employee_id = Employee.objects.filter(
            id=self.data.get("employee_id")
        ).first()

        self.errors.pop("employee_id", None)
        if self.instance.employee_id is None:
            raise ValidationError({"employee_id": _("This field is required")})
        super().clean()
        cleaned_data = super().clean()
        if "rotate_after_day" in self.errors:
            del self.errors["rotate_after_day"]
        return cleaned_data

    def save(
        self,
        commit=False,
    ):
        employee_ids = self.data.getlist("employee_id")
        rotating_shift = RotatingShift.objects.get(id=self.data["rotating_shift_id"])

        day_name = self.cleaned_data["rotate_every_weekend"]
        day_names = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        target_day = day_names.index(day_name.lower())
        for employee_id in employee_ids:
            employee = Employee.objects.filter(id=employee_id).first()
            rotating_shift_assign = RotatingShiftAssign()
            rotating_shift_assign.rotating_shift_id = rotating_shift
            rotating_shift_assign.employee_id = employee
            rotating_shift_assign.based_on = self.cleaned_data["based_on"]
            rotating_shift_assign.start_date = self.cleaned_data["start_date"]
            rotating_shift_assign.next_change_date = self.cleaned_data["start_date"]
            rotating_shift_assign.rotate_after_day = self.data.get("rotate_after_day")
            rotating_shift_assign.rotate_every = self.cleaned_data["rotate_every"]
            rotating_shift_assign.rotate_every_weekend = self.cleaned_data[
                "rotate_every_weekend"
            ]
            rotating_shift_assign.next_change_date = self.cleaned_data["start_date"]
            rotating_shift_assign.current_shift = employee.employee_work_info.shift_id
            rotating_shift_assign.next_shift = rotating_shift.shift2
            based_on = self.cleaned_data["based_on"]
            start_date = self.cleaned_data["start_date"]
            if based_on == "weekly":
                next_date = get_next_week_date(target_day, start_date)
                rotating_shift_assign.next_change_date = next_date
            elif based_on == "monthly":
                # 0, 1, 2, ..., 31, or "last"
                rotate_every = self.cleaned_data["rotate_every"]
                start_date = self.cleaned_data["start_date"]
                next_date = get_next_monthly_date(start_date, rotate_every)
                rotating_shift_assign.next_change_date = next_date
            elif based_on == "after":
                rotating_shift_assign.next_change_date = (
                    rotating_shift_assign.start_date
                    + datetime.timedelta(days=int(self.data.get("rotate_after_day")))
                )
            rotating_shift_assign.save()


class RotatingShiftAssignUpdateForm(ModelForm):
    """
    RotatingShiftAssign model's form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = RotatingShiftAssign
        fields = "__all__"
        exclude = ["next_change_date", "current_shift", "next_shift", "is_active"]
        widgets = {
            "start_date": DateInput(attrs={"type": "date"}),
        }
        labels = {
            "start_date": _trans("Start date"),
            "rotate_after_day": _trans("Rotate after day"),
            "rotate_every_weekend": _trans("Rotate every weekend"),
            "rotate_every": _trans("Rotate every"),
            "based_on": _trans("Based on"),
            "is_active": _trans("Is Active"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reload_queryset(self.fields)
        self.fields["rotate_every_weekend"].widget.attrs.update(
            {
                "class": "w-100 ",
                "style": "display:none; height:50px; border-radius:0; border:1px \
                    solid hsl(213deg,22%,84%);",
                "data-hidden": True,
            }
        )
        self.fields["rotate_every"].widget.attrs.update(
            {
                "class": "w-100 ",
                "style": "display:none; height:50px; border-radius:0; border:1px \
                    solid hsl(213deg,22%,84%);",
                "data-hidden": True,
            }
        )
        self.fields["rotate_after_day"].widget.attrs.update(
            {
                "class": "w-100 oh-input",
                "style": " height:50px; border-radius:0;",
            }
        )
        self.fields["based_on"].widget.attrs.update(
            {
                "class": "w-100",
                "style": " height:50px; border-radius:0; border:1px solid hsl(213deg,22%,84%);",
            }
        )
        self.fields["start_date"].widget = forms.DateInput(
            attrs={
                "class": "w-100 oh-input",
                "type": "date",
                "style": " height:50px; border-radius:0;",
            }
        )
        self.fields["rotating_shift_id"].widget.attrs.update(
            {
                "class": "oh-select oh-select-2",
            }
        )
        self.fields["employee_id"].widget.attrs.update(
            {
                "class": "oh-select oh-select-2",
            }
        )

    def save(self, *args, **kwargs):
        day_name = self.cleaned_data["rotate_every_weekend"]
        day_names = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        target_day = day_names.index(day_name.lower())

        based_on = self.cleaned_data["based_on"]
        start_date = self.instance.start_date
        if based_on == "weekly":
            next_date = get_next_week_date(target_day, start_date)
            self.instance.next_change_date = next_date
        elif based_on == "monthly":
            rotate_every = self.instance.rotate_every  # 0, 1, 2, ..., 31, or "last"
            start_date = self.instance.start_date
            next_date = get_next_monthly_date(start_date, rotate_every)
            self.instance.next_change_date = next_date
        elif based_on == "after":
            self.instance.next_change_date = (
                self.instance.start_date
                + datetime.timedelta(days=int(self.data.get("rotate_after_day")))
            )
        return super().save()


class ShiftRequestForm(ModelForm):
    """
    ShiftRequest model's form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = ShiftRequest
        fields = "__all__"
        exclude = [
            "reallocate_to",
            "approved",
            "canceled",
            "reallocate_approved",
            "reallocate_canceled",
            "previous_shift_id",
            "is_active",
            "shift_changed",
        ]
        widgets = {
            "requested_date": DateInput(attrs={"type": "date"}),
            "requested_till": DateInput(attrs={"type": "date"}),
        }
        labels = {
            "description": _trans("Description"),
            "requested_date": _trans("Requested Date"),
            "requested_till": _trans("Requested Till"),
        }

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("attendance_form.html", context)
        return table_html

    def save(self, commit: bool = ...):
        if not self.instance.approved:
            employee = self.instance.employee_id
            if hasattr(employee, "employee_work_info"):
                self.instance.previous_shift_id = employee.employee_work_info.shift_id
                if self.instance.is_permanent_shift:
                    self.instance.requested_till = None
        return super().save(commit)

    # here set default filter for all the employees those have work information filled.


class ShiftAllocationForm(ModelForm):
    """
    ShiftRequest model's form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = ShiftRequest
        fields = "__all__"
        exclude = (
            "is_permanent_shift",
            "approved",
            "canceled",
            "reallocate_approved",
            "reallocate_canceled",
            "previous_shift_id",
            "is_active",
            "shift_changed",
        )
        widgets = {
            "requested_date": DateInput(attrs={"type": "date"}),
            "requested_till": DateInput(attrs={"type": "date", "required": "true"}),
        }

        labels = {
            "description": _trans("Description"),
            "requested_date": _trans("Requested Date"),
            "requested_till": _trans("Requested Till"),
        }

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("attendance_form.html", context)
        return table_html

    def save(self, commit: bool = ...):
        if not self.instance.approved:
            employee = self.instance.employee_id
            if hasattr(employee, "employee_work_info"):
                self.instance.previous_shift_id = employee.employee_work_info.shift_id
                if not self.instance.requested_till:
                    self.instance.requested_till = (
                        employee.employee_work_info.contract_end_date
                    )
        return super().save(commit)


class WorkTypeRequestForm(ModelForm):
    """
    WorkTypeRequest model's form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = WorkTypeRequest
        fields = "__all__"
        exclude = (
            "approved",
            "canceled",
            "previous_work_type_id",
            "is_active",
            "work_type_changed",
        )
        widgets = {
            "requested_date": DateInput(attrs={"type": "date"}),
            "requested_till": DateInput(attrs={"type": "date"}),
        }
        labels = {
            "requested_date": _trans("Requested Date"),
            "requested_till": _trans("Requested Till"),
            "description": _trans("Description"),
        }

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("attendance_form.html", context)
        return table_html

    def save(self, commit: bool = ...):
        if not self.instance.approved:
            employee = self.instance.employee_id
            if hasattr(employee, "employee_work_info"):
                self.instance.previous_work_type_id = (
                    employee.employee_work_info.work_type_id
                )
                if self.instance.is_permanent_work_type:
                    self.instance.requested_till = None
        return super().save(commit)


class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(
        label=_("Old password"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": _("Enter Old Password"),
                "class": "oh-input oh-input--password w-100 mb-2",
            }
        ),
        help_text=_("Enter your old password."),
    )
    new_password = forms.CharField(
        label=_("New password"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": _("Enter New Password"),
                "class": "oh-input oh-input--password w-100 mb-2",
            }
        ),
    )
    confirm_password = forms.CharField(
        label=_("New password confirmation"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": _("Re-Enter Password"),
                "class": "oh-input oh-input--password w-100 mb-2",
            }
        ),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(ChangePasswordForm, self).__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get("old_password")
        if not self.user.check_password(old_password):
            raise forms.ValidationError("Incorrect old password.")
        return old_password

    def clean_new_password(self):
        new_password = self.cleaned_data.get("new_password")
        if self.user.check_password(new_password):
            raise forms.ValidationError(
                "New password must be different from the old password."
            )

        return new_password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")
        if new_password and confirm_password and new_password != confirm_password:
            raise ValidationError(
                {"new_password": _("New password and confirm password do not match")}
            )

        return cleaned_data


class ResetPasswordForm(forms.Form):
    """
    ResetPasswordForm
    """

    password = forms.CharField(
        label=_("New password"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": _("Enter Strong Password"),
                "class": "oh-input oh-input--password w-100 mb-2",
            }
        ),
        help_text=_("Enter your new password."),
    )
    confirm_password = forms.CharField(
        label=_("New password confirmation"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": _("Re-Enter Password"),
                "class": "oh-input oh-input--password w-100 mb-2",
            }
        ),
        help_text=_("Enter the same password as before, for verification."),
    )

    def clean_password(self):
        """
        Validation to password field"""
        password = self.cleaned_data.get("password")
        try:
            if len(password) < 7:
                raise ValidationError(_("Password must contain at least 8 characters."))
            elif not any(char.isupper() for char in password):
                raise ValidationError(
                    _("Password must contain at least one uppercase letter.")
                )
            elif not any(char.islower() for char in password):
                raise ValidationError(
                    _("Password must contain at least one lowercase letter.")
                )
            elif not any(char.isdigit() for char in password):
                raise ValidationError(_("Password must contain at least one digit."))
            elif all(
                char not in "!@#$%^&*()_+-=[]{}|;:,.<>?'\"`~\\/" for char in password
            ):
                raise ValidationError(
                    _("Password must contain at least one special character.")
                )
        except ValidationError as error:
            raise forms.ValidationError(list(error)[0])
        return password

    def clean_confirm_password(self):
        """
        validation method for confirm password field
        """
        password = self.cleaned_data.get("password")
        confirm_password = self.cleaned_data.get("confirm_password")
        if password == confirm_password:
            return confirm_password
        raise forms.ValidationError(_("Password must be same."))

    def save(self, *args, user=None, **kwargs):
        """
        Save method to ResetPasswordForm
        """
        if user is not None:
            user.set_password(self.data["password"])
            user.save()


excluded_fields = ["id", "is_active", "shift_changed", "work_type_changed"]


class ShiftRequestColumnForm(forms.Form):
    model_fields = ShiftRequest._meta.get_fields()
    field_choices = [
        (field.name, field.verbose_name)
        for field in model_fields
        if hasattr(field, "verbose_name") and field.name not in excluded_fields
    ]
    selected_fields = forms.MultipleChoiceField(
        choices=field_choices,
        widget=forms.CheckboxSelectMultiple,
        initial=[
            "employee_id",
            "shift_id",
            "requested_date",
            "requested_till",
            "previous_shift_id",
            "approved",
        ],
    )


class WorkTypeRequestColumnForm(forms.Form):
    model_fields = WorkTypeRequest._meta.get_fields()
    field_choices = [
        (field.name, field.verbose_name)
        for field in model_fields
        if hasattr(field, "verbose_name") and field.name not in excluded_fields
    ]
    selected_fields = forms.MultipleChoiceField(
        choices=field_choices,
        widget=forms.CheckboxSelectMultiple,
        initial=[
            "employee_id",
            "work_type_id",
            "requested_date",
            "requested_till",
            "previous_shift_id",
            "approved",
        ],
    )


class RotatingShiftAssignExportForm(forms.Form):
    model_fields = RotatingShiftAssign._meta.get_fields()
    field_choices = [
        (field.name, field.verbose_name)
        for field in model_fields
        if hasattr(field, "verbose_name") and field.name not in excluded_fields
    ]
    selected_fields = forms.MultipleChoiceField(
        choices=field_choices,
        widget=forms.CheckboxSelectMultiple,
        initial=[
            "employee_id",
            "rotating_shift_id",
            "start_date",
            "next_change_date",
            "current_shift",
            "next_shift",
            "based_on",
        ],
    )


class RotatingWorkTypeAssignExportForm(forms.Form):
    model_fields = RotatingWorkTypeAssign._meta.get_fields()
    field_choices = [
        (field.name, field.verbose_name)
        for field in model_fields
        if hasattr(field, "verbose_name") and field.name not in excluded_fields
    ]
    selected_fields = forms.MultipleChoiceField(
        choices=field_choices,
        widget=forms.CheckboxSelectMultiple,
        initial=[
            "employee_id",
            "rotating_work_type_id",
            "start_date",
            "next_change_date",
            "current_work_type",
            "next_work_type",
            "based_on",
        ],
    )


class TagsForm(ModelForm):
    """
    Tags form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = Tags
        fields = "__all__"
        widgets = {"color": TextInput(attrs={"type": "color", "style": "height:50px"})}
        exclude = ["objects", "is_active"]


class EmployeeTagForm(ModelForm):
    """
    Employee Tags form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = EmployeeTag
        fields = "__all__"
        exclude = ["is_active"]
        widgets = {"color": TextInput(attrs={"type": "color", "style": "height:50px"})}


class AuditTagForm(ModelForm):
    """
    Audit Tags form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = AuditTag
        fields = "__all__"


class ShiftRequestCommentForm(ModelForm):
    """
    Shift request comment form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = ShiftRequestComment
        fields = ("comment",)


class WorkTypeRequestCommentForm(ModelForm):
    """
    WorkType request comment form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = WorkTypeRequestComment
        fields = ("comment",)


class DynamicMailConfForm(ModelForm):
    """
    DynamicEmailConfiguration
    """

    class Meta:
        model = DynamicEmailConfiguration
        fields = "__all__"

    def as_p(self):
        """
        Render the form fields as HTML table rows with Bootstrap styling.
        """
        context = {"form": self}
        table_html = render_to_string("attendance_form.html", context)
        return table_html


class MultipleApproveConditionForm(ModelForm):
    CONDITION_CHOICE = [
        ("equal", _("Equal (==)")),
        ("notequal", _("Not Equal (!=)")),
        ("range", _("Range")),
        ("lt", _("Less Than (<)")),
        ("gt", _("Greater Than (>)")),
        ("le", _("Less Than or Equal To (<=)")),
        ("ge", _("Greater Than or Equal To (>=)")),
        ("icontains", _("Contains")),
    ]
    multi_approval_manager = forms.ModelChoiceField(
        queryset=Employee.objects.all(),
        widget=forms.Select(attrs={"class": "oh-select oh-select-2 mb-2"}),
        label=_("Approval Manager"),
        required=True,
    )
    condition_operator = forms.ChoiceField(
        choices=CONDITION_CHOICE,
        widget=forms.Select(
            attrs={
                "class": "oh-select oh-select-2 mb-2",
                "onChange": "toggleFields($('#id_condition_operator'))",
            },
        ),
    )

    class Meta:
        model = MultipleApprovalCondition
        fields = "__all__"
        exclude = [
            "is_active",
        ]


class DynamicPaginationForm(ModelForm):
    """
    Form for setting default pagination
    """

    class Meta:
        model = DynamicPagination
        fields = "__all__"
        exclude = ("user_id",)


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [
                single_file_clean(data, initial),
            ]
        return result[0] if result else None


class AnnouncementForm(ModelForm):
    """
    Announcement Form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = Announcement
        fields = "__all__"
        widgets = {
            "description": forms.Textarea(attrs={"data-summernote": ""}),
            "expire_date": DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["attachments"] = MultipleFileField(label="Attachments ")
        self.fields["attachments"].required = False

    def save(self, commit: bool = ...) -> Any:
        attachement = []
        multiple_attachment_ids = []
        attachements = None
        if self.files.getlist("attachments"):
            attachements = self.files.getlist("attachments")
            self.instance.attachement = attachements[0]
            multiple_attachment_ids = []

            for attachement in attachements:
                file_instance = Attachment()
                file_instance.file = attachement
                file_instance.save()
                multiple_attachment_ids.append(file_instance.pk)
        instance = super().save(commit)
        if commit:
            instance.attachements.add(*multiple_attachment_ids)
        return instance, multiple_attachment_ids


class AnnouncementcommentForm(ModelForm):
    """
    Announcement comment form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = AnnouncementComment
        fields = ("comment",)


class AnnouncementExpireForm(ModelForm):
    """
    Announcement Expire form
    """

    class Meta:
        """
        Meta class for additional options
        """

        model = AnnouncementExpire
        fields = ("days",)


class DriverForm(forms.ModelForm):
    """
    DriverForm
    """

    class Meta:
        model = DriverViewed
        fields = "__all__"
