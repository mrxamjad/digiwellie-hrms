"""
surveys.py

This module is used to write views related to the survey features
"""

import json
from datetime import datetime
from django.core.files.storage import default_storage
from django.core import serializers
from django.db.models import ProtectedError
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from base.methods import closest_numbers
from horilla.decorators import login_required, permission_required
from recruitment.models import Recruitment, SurveyTemplate
from recruitment.forms import (
    AddQuestionForm,
    ApplicationForm,
    SurveyForm,
    QuestionForm,
    TemplateForm,
)
from recruitment.models import (
    RecruitmentSurvey,
    Candidate,
    JobPosition,
    Stage,
    RecruitmentSurveyAnswer,
)
from recruitment.filters import SurveyFilter
from recruitment.pipeline_grouper import group_by_queryset
from recruitment.views.paginator_qry import paginator_qry


def survey_form(request):
    """
    This method is used to render survey wform
    """
    recruitment_id = request.GET["recId"]
    recruitment = Recruitment.objects.get(id=recruitment_id)
    form = SurveyForm(recruitment=recruitment).form
    return render(request, "survey/form.html", {"form": form})


def candidate_survey(request):
    """
    Used to render survey form to the candidate
    """
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB in bytes
    candidate_json = request.session["candidate"]
    candidate_dict = json.loads(candidate_json)
    rec_id = candidate_dict[0]["fields"]["recruitment_id"]
    job_id = candidate_dict[0]["fields"]["job_position_id"]
    job = JobPosition.objects.get(id=job_id)
    recruitment = Recruitment.objects.get(id=rec_id)
    stage_id = candidate_dict[0]["fields"]["stage_id"]
    candidate_dict[0]["fields"]["recruitment_id"] = recruitment
    candidate_dict[0]["fields"]["job_position_id"] = job
    candidate_dict[0]["fields"]["stage_id"] = Stage.objects.get(id=stage_id)
    candidate = Candidate(**candidate_dict[0]["fields"])
    form = SurveyForm(recruitment=recruitment).form
    if request.method == "POST":
        if not Candidate.objects.filter(
            email=candidate.email, recruitment_id=candidate.recruitment_id
        ).exists():
            candidate.save()
        else:
            candidate = Candidate.objects.filter(
                email=candidate.email, recruitment_id=candidate.recruitment_id
            ).first()
        answer = (
            RecruitmentSurveyAnswer()
            if candidate.recruitmentsurveyanswer_set.first() is None
            else candidate.recruitmentsurveyanswer_set.first()
        )
        answer.candidate_id = candidate

        # Process the POST data to properly handle multiple values
        answer_data = {}
        for key, value in request.POST.items():
            if key.startswith("multiple_choices_"):
                parts = key.split("_", 2)
                question_text = parts[2]
                selected_choices = request.POST.getlist(key)
                answer_data[question_text] = selected_choices
            elif key.startswith("date_"):
                parts = key.split("_", 1)
                question_text = parts[1]
                selected_choices = request.POST.getlist(key)
                if selected_choices and selected_choices[0] != "":
                    formatted_dates = [
                        datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y")
                        for date in selected_choices
                    ]
                    answer_data[question_text] = formatted_dates
            else:
                answer_data[key] = [value]
        for key, value in request.FILES.items():
            attachment = request.FILES[key]
            if attachment.size > MAX_FILE_SIZE:
                messages.error(
                    request, _("File size exceeds the limit. Maximum size is 5 MB")
                )
                return render(
                    request,
                    "survey/candidate_survey_form.html",
                    {"form": form, "candidate": candidate},
                )
            attachment_path = f"recruitment_attachment/{attachment.name}"
            with default_storage.open(attachment_path, "wb+") as destination:
                for chunk in attachment.chunks():
                    destination.write(chunk)
            answer.attachment = attachment_path
            answer_data[key] = [attachment_path]
        answer.answer_json = json.dumps(answer_data)
        answer.save()
        messages.success(request, _("Your answers are submitted."))
        return render(request, "candidate/success.html")
    return render(
        request,
        "survey/candidate_survey_form.html",
        {"form": form, "candidate": candidate},
    )


@login_required
@permission_required(perm="recruitment.view_recruitmentsurvey")
def view_question_template(request):
    """
    This method is used to view the question template
    """
    questions = RecruitmentSurvey.objects.all()
    templates = group_by_queryset(
        questions.filter(template_id__isnull=False).distinct(),
        "template_id__title",
        page=request.GET.get("template_page"),
        page_name="template_page",
        records_per_page=50,
    )
    all_template_object_list = []
    for template in templates:
        all_template_object_list.append(template)

    survey_templates = SurveyTemplate.objects.all()
    all_templates = survey_templates.values_list("title", flat=True)
    used_templates = questions.values_list("template_id__title", flat=True)

    unused_templates = list(set(all_templates) - set(used_templates))
    unused_groups = []
    for template_name in unused_templates:
        unused_groups.append(
            {
                "grouper": template_name,
                "list": [],
                "dynamic_name": "",
            }
        )
    all_template_object_list = all_template_object_list + unused_groups

    templates = paginator_qry(
        all_template_object_list, request.GET.get("template_page")
    )
    survey_templates = paginator_qry(
        survey_templates, request.GET.get("survey_template_page")
    )
    filter_obj = SurveyFilter()
    requests_ids = json.dumps(
        [
            instance.id
            for instance in paginator_qry(
                questions, request.GET.get("page")
            ).object_list
        ]
    )
    return render(
        request,
        "survey/view_question_templates.html",
        {
            "questions": paginator_qry(questions, request.GET.get("page")),
            "templates": templates,
            "survey_templates": survey_templates,
            "f": filter_obj,
            "requests_ids": requests_ids,
        },
    )


@login_required
@permission_required(perm="recruitment.change_recruitmentsurvey")
def update_question_template(request, survey_id):
    """
    This view method is used to update question template
    """
    instance = RecruitmentSurvey.objects.get(id=survey_id)
    form = QuestionForm(
        instance=instance,
    )
    if request.method == "POST":
        form = QuestionForm(request.POST, instance=instance)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            instance.template_id.set(form.cleaned_data["template_id"])
            instance.recruitment_ids.set(form.recruitment)
            # instance.job_position_ids.set(form.job_positions)
            messages.success(request, _("New survey question updated."))
            return HttpResponse(
                render(
                    request, "survey/template_update_form.html", {"form": form}
                ).content.decode("utf-8")
                + "<script>location.reload();</script>"
            )
    return render(request, "survey/template_update_form.html", {"form": form})


@login_required
@permission_required(perm="recruitment.add_recruitmentsurvey")
def create_question_template(request):
    """
    This view method is used to create question template
    """
    form = QuestionForm()
    if request.method == "POST":
        form = QuestionForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            instance.recruitment_ids.set(form.recruitment)
            instance.template_id.set(form.cleaned_data["template_id"])
            # instance.job_position_ids.set(form.job_positions)
            messages.success(request, _("New survey question created."))
            return HttpResponse(
                render(
                    request, "survey/template_form.html", {"form": form}
                ).content.decode("utf-8")
                + "<script>location.reload();</script>"
            )
    return render(request, "survey/template_form.html", {"form": form})


@login_required
@permission_required(perm="recriutment.delete_recruitmentsurvey")
def delete_survey_question(request, survey_id):
    """
    This method is used to delete the survey instance
    """
    try:
        RecruitmentSurvey.objects.get(id=survey_id).delete()
        messages.success(request, _("Question was deleted successfully"))
    except RecruitmentSurvey.DoesNotExist:
        messages.error(request, _("Question not found."))
    except ProtectedError:
        messages.error(request, _("You cannot delete this question"))
    return redirect(view_question_template)


def application_form(request):
    """
    This method renders candidate form to create candidate
    """
    form = ApplicationForm()
    recruitment = None
    recruitment_id = request.GET.get("recruitmentId")
    if recruitment_id is not None:
        recruitment = Recruitment.objects.filter(id=recruitment_id)
        if recruitment.exists():
            recruitment = recruitment.first()
    if request.POST:
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            candidate_obj = form.save(commit=False)
            recruitment_obj = candidate_obj.recruitment_id
            stages = recruitment_obj.stage_set.all()
            if stages.filter(stage_type="initial").exists():
                candidate_obj.stage_id = stages.filter(stage_type="initial").first()
            else:
                candidate_obj.stage_id = stages.order_by("sequence").first()
            messages.success(request, _("Application saved."))

            resume = request.FILES["resume"]
            profile = request.FILES["profile"]

            resume_path = f"recruitment/resume/{resume.name}"
            profile_path = f"recruitment/profile/{profile.name}"

            with default_storage.open(resume_path, "wb+") as destination:
                for chunk in resume.chunks():
                    destination.write(chunk)

            with default_storage.open(profile_path, "wb+") as destination:
                for chunk in profile.chunks():
                    destination.write(chunk)

            candidate_obj.resume = resume_path
            candidate_obj.profile = profile_path

            request.session["candidate"] = serializers.serialize(
                "json", [candidate_obj]
            )
            return redirect(candidate_survey)
        form.fields["job_position_id"].queryset = (
            form.instance.recruitment_id.open_positions.all()
        )
    return render(
        request,
        "candidate/application_form.html",
        {"form": form, "recruitment": recruitment},
    )


@login_required
@permission_required(perm="recruitment.view_recruitmentsurvey")
def single_survey(request, survey_id):
    """
    This view method is used to single view of question template
    """
    question = RecruitmentSurvey.objects.get(id=survey_id)
    requests_ids_json = request.GET.get("instances_ids")
    context = {"question": question}
    if requests_ids_json:
        requests_ids = json.loads(requests_ids_json)
        previous_id, next_id = closest_numbers(requests_ids, survey_id)
        context["previous"] = previous_id
        context["next"] = next_id
        context["requests_ids"] = requests_ids_json
    return render(request, "survey/view_single_template.html", context)


@login_required
@permission_required("recruitment.add_surveytemplate")
def create_template(request):
    """
    Create question template views
    """
    title = request.GET.get("title")
    instance = None
    if title:
        instance = SurveyTemplate.objects.filter(title=title).first()
    form = TemplateForm(instance=instance)
    if request.method == "POST":
        form = TemplateForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Template saved")
            return HttpResponse("<script>window.location.reload()</script>")
    return render(request, "survey/main_form.html", {"form": form})


@login_required
@permission_required("recruitment.delete_surveytemplate")
def delete_template(request):
    """
    This method is used to delete the survey template group
    """
    title = request.GET.get("title")
    SurveyTemplate.objects.filter(title=str(title)).delete()
    if title == "None":
        messages.info(request, "This template group cannot be deleted")
    else:
        messages.success(request, "Template group deleted")

    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@permission_required("recruitment.change_surveytemplate")
def question_add(request):
    """
    This method is used to add survey question to the templates
    """
    template = None
    title = request.GET.get("title")
    if title:
        template = SurveyTemplate.objects.filter(title=title)

    form = AddQuestionForm(initial={"template_ids": template})
    if request.method == "POST":
        form = AddQuestionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Question added")
            return HttpResponse("<script>window.location.reload()</script>")
    return render(request, "survey/add_form.html", {"form": form})
