"""
admin.py

This page is used to register the model with admins site.
"""

from django.contrib import admin
from recruitment.models import (
    CandidateRating,
    SkillZone,
    Stage,
    Recruitment,
    Candidate,
    RecruitmentSurvey,
    RecruitmentSurveyAnswer,
    RecruitmentMailTemplate,
)


# Register your models here.


admin.site.register(Stage)
admin.site.register(Recruitment)
admin.site.register(Candidate)
admin.site.register(RecruitmentSurveyAnswer)
admin.site.register(RecruitmentSurvey)
admin.site.register(RecruitmentMailTemplate)
admin.site.register(CandidateRating)
admin.site.register(SkillZone)
