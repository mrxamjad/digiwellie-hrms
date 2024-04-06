"""
horilla_context_process.py

This module is used to register context processors without effecting the horilla/settings.py module
"""

from horilla.settings import TEMPLATES

TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "base.context_processors.get_companies",
)
TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "base.context_processors.resignation_request_enabled",
)
TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "base.context_processors.timerunner_enabled",
)
TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "base.context_processors.intial_notice_period",
)
TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "base.context_processors.check_candidate_self_tracking",
)
TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "base.context_processors.check_candidate_self_tracking_rating",
)

TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "base.context_processors.get_intial_prefix",
)
