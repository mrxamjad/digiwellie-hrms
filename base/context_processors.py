"""
context_processor.py

This module is used to register context processor`
"""

from django.urls import path
from django.http import HttpResponse
from attendance.models import AttendanceGeneralSetting
from base.models import Company
from base.urls import urlpatterns
from employee.models import EmployeeGeneralSetting
from offboarding.models import OffboardingGeneralSetting
from payroll.models.models import PayrollGeneralSetting
from recruitment.models import RecruitmentGeneralSetting


class AllCompany:
    """
    Dummy class
    """

    class Urls:
        url = "data:image/jpeg;base64,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"

    company = "DigiWellie Technology"
    icon = Urls()
    text = ""
    id = None


def get_companies(request):
    """
    This method will return the history additional field form
    """
    companies = list(
        [company.id, company.company, company.icon.url, False]
        for company in Company.objects.all()
    )
    companies = [
        [
            "all",
            "All Company",
            "https://ui-avatars.com/api/?name=All+Company&background=random",
            False,
        ],
    ] + companies
    selected_company = request.session.get("selected_company")
    company_selected = False
    if selected_company and selected_company == "all":
        companies[0][3] = True
        company_selected = True
    else:
        for company in companies:
            if str(company[0]) == selected_company:
                company[3] = True
                company_selected = True
    return {"all_companies": companies, "company_selected": company_selected}


def update_selected_company(request):
    """
    This method is used to update the selected company on the session
    """
    company_id = request.GET.get("company_id")
    request.session["selected_company"] = company_id
    company = (
        AllCompany()
        if company_id == "all"
        else (
            Company.objects.filter(id=company_id).first()
            if Company.objects.filter(id=company_id).first()
            else AllCompany()
        )
    )

    text = "Other Company"
    if company_id == request.user.employee_get.employee_work_info.company_id:
        text = "My Company"
    if company_id == "all":
        text = "All companies"
    company = {
        "company": company.company,
        "icon": company.icon.url,
        "text": text,
        "id": company.id,
    }
    request.session["selected_company_instance"] = company
    return HttpResponse("<script>window.location.reload();</script>")


urlpatterns.append(
    path(
        "update-selected-company",
        update_selected_company,
        name="update-selected-company",
    )
)


def resignation_request_enabled(request):
    """
    Check weather resignation_request enabled of not in offboarding
    """
    first = OffboardingGeneralSetting.objects.first()
    enabled_resignation_request = True
    if first:
        enabled_resignation_request = first.resignation_request
    return {"enabled_resignation_request": enabled_resignation_request}


def timerunner_enabled(request):
    """
    Check weather resignation_request enabled of not in offboarding
    """
    first = AttendanceGeneralSetting.objects.first()
    enabled_timerunner = True
    if first:
        enabled_timerunner = first.time_runner
    return {"enabled_timerunner": enabled_timerunner}


def intial_notice_period(request):
    """
    Check weather resignation_request enabled of not in offboarding
    """
    first = PayrollGeneralSetting.objects.first()
    initial = 30
    if first:
        initial = first.notice_period
    return {"get_initial_notice_period": initial}


def check_candidate_self_tracking(request):
    """
    This method is used to get the candidate self tracking is enabled or not
    """
    first = RecruitmentGeneralSetting.objects.first()
    candidate_self_tracking = False
    if first:
        candidate_self_tracking = first.candidate_self_tracking
    return {"check_candidate_self_tracking": candidate_self_tracking}


def check_candidate_self_tracking_rating(request):
    """
    This method is used to check enabled/disabled of rating option
    """
    first = RecruitmentGeneralSetting.objects.first()
    rating_option = False
    if first:
        rating_option = first.show_overall_rating
    return {"check_candidate_self_tracking_rating": rating_option}


def get_intial_prefix(request):
    """
    This method is used to get the initial prefexi
    """
    settings = EmployeeGeneralSetting.objects.first()
    instance_id = None
    prefix = "PEP"
    if settings:
        instance_id = settings.id
        prefix = settings.badge_id_prefix
    return {"get_intial_prefix": prefix, "prefix_instance_id": instance_id}
