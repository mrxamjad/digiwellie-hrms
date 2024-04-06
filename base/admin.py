"""
admin.py

This page is used to register base models with admins site.
"""

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from base.models import (
    Announcement,
    Attachment,
    Company,
    Department,
    DynamicEmailConfiguration,
    DynamicPagination,
    EmailLog,
    JobPosition,
    JobRole,
    EmployeeShiftSchedule,
    EmployeeShift,
    EmployeeShiftDay,
    EmployeeType,
    MultipleApprovalManagers,
    ShiftRequestComment,
    Tags,
    WorkType,
    RotatingWorkType,
    RotatingWorkTypeAssign,
    RotatingShift,
    RotatingShiftAssign,
    ShiftRequest,
    WorkTypeRequest,
    WorkTypeRequestComment,
    DashboardEmployeeCharts,
)

# Register your models here.

admin.site.register(Company)
admin.site.register(Department, SimpleHistoryAdmin)
admin.site.register(JobPosition)
admin.site.register(JobRole)
admin.site.register(EmployeeShift)
admin.site.register(EmployeeShiftSchedule)
admin.site.register(EmployeeShiftDay)
admin.site.register(EmployeeType)
admin.site.register(WorkType)
admin.site.register(RotatingWorkType)
admin.site.register(RotatingWorkTypeAssign)
admin.site.register(RotatingShift)
admin.site.register(RotatingShiftAssign)
admin.site.register(ShiftRequest)
admin.site.register(WorkTypeRequest)
admin.site.register(Tags)
admin.site.register(DynamicEmailConfiguration)
admin.site.register(MultipleApprovalManagers)
admin.site.register(ShiftRequestComment)
admin.site.register(WorkTypeRequestComment)
admin.site.register(DynamicPagination)
admin.site.register(Announcement)
admin.site.register(Attachment)
admin.site.register(EmailLog)
admin.site.register(DashboardEmployeeCharts)