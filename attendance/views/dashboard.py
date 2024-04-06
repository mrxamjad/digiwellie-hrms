"""
dashboard.py

This module is used to register endpoints for dashboard-related requests
"""

import calendar
from datetime import date, datetime, timedelta
from django.db.models import Q, Sum
from django.shortcuts import render
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from attendance.filters import (
    AttendanceFilters,
    LateComeEarlyOutFilter,
    AttendanceOverTimeFilter,
)
from attendance.models import (
    Attendance,
    AttendanceLateComeEarlyOut,
    AttendanceOverTime,
    AttendanceValidationCondition,
)
from attendance.views.views import strtime_seconds
from base.methods import filtersubordinates
from base.models import Department, EmployeeShiftSchedule
from employee.models import Employee
from employee.not_in_out_dashboard import paginator_qry
from horilla.decorators import login_required
from leave.models import LeaveRequest


def find_on_time(request, today, week_day, department=None):
    """
    This method is used to find count for on time attendances
    """

    on_time = 0
    attendances = Attendance.objects.filter(attendance_date=today)
    if department is not None:
        attendances = attendances.filter(
            employee_id__employee_work_info__department_id=department
        )
    late_come = AttendanceLateComeEarlyOut.objects.filter(
        attendance_id__attendance_date=today, type="late_come"
    )
    on_time = len(attendances) - len(late_come)
    return on_time


def find_expected_attendances(week_day):
    """
    This method is used to find count of expected attendances for the week day
    """
    employees = Employee.objects.filter(is_active=True)
    on_leave = LeaveRequest.objects.filter(status="Approved")
    expected_attendances = len(employees) - len(on_leave)
    return expected_attendances


@login_required
def dashboard(request):
    """
    This method is used to render individual dashboard for attendance module
    """
    page_number = request.GET.get("page")
    previous_data = request.GET.urlencode()
    employees = Employee.objects.filter(
        is_active=True,
    ).filter(~Q(employee_work_info__shift_id=None))
    total_employees = len(employees)

    today = datetime.today()
    week_day = today.strftime("%A").lower()

    on_time = find_on_time(request, today=today, week_day=week_day)
    late_come = find_late_come(start_date=today)
    late_come_obj = len(late_come)

    marked_attendances = late_come_obj + on_time

    expected_attendances = find_expected_attendances(week_day=week_day)
    on_time_ratio = 0
    late_come_ratio = 0
    marked_attendances_ratio = 0
    if expected_attendances != 0:
        on_time_ratio = f"{(on_time / expected_attendances) * 100:.2f}"
        late_come_ratio = f"{(late_come_obj / expected_attendances) * 100:.2f}"
        marked_attendances_ratio = (
            f"{(marked_attendances / expected_attendances) * 100:.2f}"
        )
    early_outs = AttendanceLateComeEarlyOut.objects.filter(
        type="early_out", attendance_id__attendance_date=today
    )

    condition = AttendanceValidationCondition.objects.first()
    min_ot = strtime_seconds("00:00")
    if condition is not None and condition.minimum_overtime_to_approve is not None:
        min_ot = strtime_seconds(condition.minimum_overtime_to_approve)
    ot_attendances = Attendance.objects.filter(
        overtime_second__gte=min_ot,
        attendance_validated=True,
        employee_id__is_active=True,
        attendance_overtime_approve=False,
    )

    validate_attendances = Attendance.objects.filter(
        attendance_validated=False, employee_id__is_active=True
    )

    return render(
        request,
        "attendance/dashboard/dashboard.html",
        {
            "total_employees": total_employees,
            "on_time": on_time,
            "on_time_ratio": on_time_ratio,
            "late_come": late_come_obj,
            "late_come_ratio": late_come_ratio,
            "expected_attendances": expected_attendances,
            "marked_attendances": marked_attendances,
            "marked_attendances_ratio": marked_attendances_ratio,
            "on_break": early_outs,
            "overtime_attendances": ot_attendances,
            "validate_attendances": paginator_qry(validate_attendances, page_number),
            "pd": previous_data,
        },
    )


@login_required
def validated_attendances_table(request):
    page_number = request.GET.get("page")
    previous_data = request.GET.urlencode()
    validate_attendances = Attendance.objects.filter(
        attendance_validated=False, employee_id__is_active=True
    )
    context = {
        "validate_attendances": paginator_qry(validate_attendances, page_number),
        "pd": previous_data,
    }

    return render(request, "attendance/dashboard/to_validate_table.html", context)


def total_attendance(start_date, department, end_date=None):
    """
    This method is used to find total attendance
    """
    attendance = AttendanceFilters(
        {
            "attendance_date__gte": start_date,
            "attendance_date__lte": end_date,
            "department": department,
        }
    ).qs
    return attendance


def find_late_come(start_date, department=None, end_date=None):
    """
    This method is used to find late comers
    """
    if department is not None:
        late_come_obj = LateComeEarlyOutFilter(
            {
                "type": "late_come",
                "department": department,
                "attendance_date__gte": start_date,
                "attendance_date__lte": end_date,
            }
        ).qs
    else:
        late_come_obj = LateComeEarlyOutFilter(
            {
                "type": "late_come",
                "attendance_date__gte": start_date,
                "attendance_date__lte": end_date,
            }
        ).qs
    return late_come_obj


def find_early_out(start_date, end_date=None, department=None):
    """
    This method is used to find early out attendances and it returns query set
    """
    if department is not None:
        early_out_obj = LateComeEarlyOutFilter(
            {
                "type": "early_out",
                "department": department,
                "attendance_date__gte": start_date,
                "attendance_date__lte": end_date,
            }
        ).qs
    else:
        early_out_obj = LateComeEarlyOutFilter(
            {
                "type": "early_out",
                "attendance_date__gte": start_date,
                "attendance_date__lte": end_date,
            }
        ).qs
    return early_out_obj


def get_week_start_end_dates(week):
    """
    This method is use to return the start and end date of the week
    """
    # Parse the ISO week date
    year, week_number = map(int, week.split("-W"))

    # Get the date of the first day of the week
    start_date = datetime.strptime(f"{year}-W{week_number}-1", "%Y-W%W-%w").date()

    # Calculate the end date by adding 6 days to the start date
    end_date = start_date + timedelta(days=6)

    return start_date, end_date


def get_month_start_end_dates(year_month):
    """
    This method is use to return the start and end date of the month
    """
    # split year and month separately
    year, month = map(int, year_month.split("-"))
    # Get the first day of the month
    start_date = datetime(year, month, 1).date()

    # Get the last day of the month
    _, last_day = calendar.monthrange(year, month)
    end_date = datetime(year, month, last_day).date()

    return start_date, end_date


def generate_data_set(request, start_date, type, end_date, dept):
    """
    This method is used to generate all the dashboard data
    """
    attendance = []
    late_come_obj = []
    early_out_obj = []
    on_time = 0
    if type == "day":
        start_date = start_date
        end_date = start_date
    if type == "weekly":
        start_date, end_date = get_week_start_end_dates(start_date)
    if type == "monthly":
        start_date, end_date = get_month_start_end_dates(start_date)
    if type == "date_range":
        start_date = start_date
        end_date = end_date
    # below method will find all the on-time attendance corresponding to the
    # employee shift and shift schedule.
    attendance = total_attendance(
        start_date=start_date, department=dept, end_date=end_date
    )

    # below method will find all the late-come attendance corresponding to the
    # employee shift and schedule.
    late_come_obj = find_late_come(
        start_date=start_date, department=dept, end_date=end_date
    )

    # below method will find all the early-out attendance corresponding to the
    # employee shift and shift schedule
    early_out_obj = find_early_out(
        department=dept, start_date=start_date, end_date=end_date
    )
    on_time = len(attendance) - len(late_come_obj)

    data = {}
    if on_time or late_come_obj or early_out_obj:
        data = {
            "label": dept.department,
            "data": [on_time, len(late_come_obj), len(early_out_obj)],
        }

    return data if data else None


@login_required
def dashboard_attendance(request):
    """
    This method is used to render json response of dashboard data

    Returns:
        JsonResponse: returns data set as json
    """
    labels = [
        _("On Time"),
        _("Late Come"),
        _("Early Out"),
    ]
    # initializing values
    data_set = []
    start_date = date.today()
    end_date = start_date
    type = "date"

    # if there is values in request update the values
    if request.GET.get("date"):
        start_date = request.GET.get("date")
    if request.GET.get("type"):
        type = request.GET.get("type")
    if request.GET.get("end_date"):
        end_date = request.GET.get("end_date")

    # get all departments for filtration
    departments = Department.objects.all()
    for dept in departments:
        data_set.append(generate_data_set(request, start_date, type, end_date, dept))
    message = _("No data Found...")
    data_set = list(filter(None, data_set))
    return JsonResponse({"dataSet": data_set, "labels": labels, "message": message})


def worked_hour_data(labels, records):
    """
    To find all the worked hours
    """
    data = {
        "label": "Worked Hours",
        "backgroundColor": "rgba(75, 192, 192, 0.6)",
    }
    dept_records = []
    for dept in labels:
        total_sum = records.filter(
            employee_id__employee_work_info__department_id__department=dept
        ).aggregate(total_sum=Sum("hour_account_second"))["total_sum"]
        dept_records.append(total_sum / 3600 if total_sum else 0)
    data["data"] = dept_records
    return data


def pending_hour_data(labels, records):
    """
    To find all the pending hours
    """
    data = {
        "label": "Pending Hours",
        "backgroundColor": "rgba(255, 99, 132, 0.6)",
    }
    dept_records = []
    for dept in labels:
        total_sum = records.filter(
            employee_id__employee_work_info__department_id__department=dept
        ).aggregate(total_sum=Sum("hour_pending_second"))["total_sum"]
        dept_records.append(total_sum / 3600 if total_sum else 0)
    data["data"] = dept_records
    return data


def pending_hours(request):
    """
    pending hours chart dashboard view
    """
    records = AttendanceOverTimeFilter(request.GET).qs
    labels = list(Department.objects.values_list("department", flat=True))
    data = {
        "labels": labels,
        "datasets": [
            pending_hour_data(labels, records),
            worked_hour_data(labels, records),
        ],
    }

    return JsonResponse({"data": data})


@login_required
def department_overtime_chart(request):
    start_date = request.GET.get("date") if request.GET.get("date") else date.today()
    chart_type = request.GET.get("type") if request.GET.get("type") else "day"
    end_date = (
        request.GET.get("end_date") if request.GET.get("end_date") else start_date
    )

    if chart_type == "day":
        start_date = start_date
        end_date = start_date
    if chart_type == "weekly":
        start_date, end_date = get_week_start_end_dates(start_date)
    if chart_type == "monthly":
        start_date, end_date = get_month_start_end_dates(start_date)
    if chart_type == "date_range":
        start_date = start_date
        end_date = end_date

    attendance = total_attendance(
        start_date=start_date, department=None, end_date=end_date
    )

    condition = AttendanceValidationCondition.objects.first()
    min_ot = strtime_seconds("00:00")
    if condition is not None and condition.minimum_overtime_to_approve is not None:
        min_ot = strtime_seconds(condition.minimum_overtime_to_approve)
    attendances = attendance.filter(
        overtime_second__gte=min_ot,
        attendance_validated=True,
        employee_id__is_active=True,
        attendance_overtime_approve=True,
    )
    departments = []
    department_total = []

    for attendance in attendances:
        departments.append(
            attendance.employee_id.employee_work_info.department_id.department
        )
    departments = list(set(departments))

    for depart in departments:
        department_total.append({"department": depart, "ot_hours": 0})

    for attendance in attendances:
        if attendance.employee_id.employee_work_info.department_id:
            department = (
                attendance.employee_id.employee_work_info.department_id.department
            )
            ot = attendance.approved_overtime_second
            ot_hrs = ot / 3600
            for depart in department_total:
                if depart["department"] == department:
                    depart["ot_hours"] += ot_hrs

    dataset = [
        {
            "label": "",
            "data": [],
        }
    ]

    for depart_total, depart in zip(department_total, departments):
        if depart == depart_total["department"]:
            dataset[0]["data"].append(depart_total["ot_hours"])

    response = {
        "dataset": dataset,
        "labels": departments,
        "department_total": department_total,
        "message": _("No validated Overtimes were found"),
        "emptyImageSrc": "/static/images/ui/overtime-icon.png",
    }

    return JsonResponse(response)
