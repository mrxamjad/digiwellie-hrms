"""
urls.py

This module is used to map url path with view methods.
"""

from django.urls import path

from base.views import object_delete
from helpdesk import views
from helpdesk.models import FAQ, FAQCategory, Ticket

urlpatterns = [
    path("faq-category-view/", views.faq_category_view, name="faq-category-view"),
    path("faq-category-create/", views.faq_category_create, name="faq-category-create"),
    path(
        "faq-category-update/<int:id>/",
        views.faq_category_update,
        name="faq-category-update",
    ),
    path(
        "faq-category-delete/<int:id>/",
        views.faq_category_delete,
        name="faq-category-delete",
    ),
    path("faq-category-search/", views.faq_category_search, name="faq-category-search"),
    path(
        "faq-view/<int:cat_id>/",
        views.faq_view,
        name="faq-view",
        kwargs={"model": FAQCategory},
    ),
    path("faq-create/<int:cat_id>/", views.create_faq, name="faq-create"),
    path("faq-update/<int:id>", views.faq_update, name="faq-update"),
    path("faq-search/", views.faq_search, name="faq-search"),
    path("faq-filter/<int:id>/", views.faq_filter, name="faq-filter"),
    path("faq-suggestion/", views.faq_suggestion, name="faq-suggestion"),
    path(
        "faq-delete/<int:id>/",
        views.faq_delete,
        name="faq-delete",
    ),
    path("ticket-view/", views.ticket_view, name="ticket-view"),
    path("ticket-create", views.ticket_create, name="ticket-create"),
    path("ticket-update/<int:ticket_id>", views.ticket_update, name="ticket-update"),
    path("ticket-archive/<int:ticket_id>", views.ticket_archive, name="ticket-archive"),
    path(
        "change-ticket-status/<int:ticket_id>/",
        views.change_ticket_status,
        name="change-ticket-status",
    ),
    path("ticket-delete/<int:ticket_id>", views.ticket_delete, name="ticket-delete"),
    path("ticket-filter", views.ticket_filter, name="ticket-filter"),
    path(
        "ticket-detail/<int:ticket_id>/",
        views.ticket_detail,
        name="ticket-detail",
        kwargs={"model": Ticket},
    ),
    path("ticket-change-tag", views.ticket_update_tag, name="ticket-change-tag"),
    path(
        "ticket-change-raised-on/<int:ticket_id>",
        views.ticket_change_raised_on,
        name="ticket-change-raised-on",
    ),
    path(
        "ticket-change-assignees/<int:ticket_id>",
        views.ticket_change_assignees,
        name="ticket-change-assignees",
    ),
    path("ticket-create-tag", views.create_tag, name="ticket-create-tag"),
    path("remove-tag", views.remove_tag, name="remove-tag"),
    path("comment-create/<int:ticket_id>", views.comment_create, name="comment-create"),
    path("comment-edit/", views.comment_edit, name="comment-edit"),
    path(
        "comment-delete/<int:comment_id>/", views.comment_delete, name="comment-delete"
    ),
    path("get-raised-on", views.get_raised_on, name="get-raised-on"),
    path("claim-ticket/<int:id>", views.claim_ticket, name="claim-ticket"),
    path(
        "tickets-select-filter",
        views.tickets_select_filter,
        name="tickets-select-filter",
    ),
    path(
        "tickets-bulk-archive", views.tickets_bulk_archive, name="tickets-bulk-archive"
    ),
    path("tickets-bulk-delete", views.tickets_bulk_delete, name="tickets-bulk-delete"),
    path(
        "department-manager-create/",
        views.create_department_manager,
        name="department-manager-create",
    ),
    path(
        "department-manager-update/<int:dep_id>",
        views.update_department_manager,
        name="department-manager-update",
    ),
    path(
        "department-manager-delete/<int:dep_id>",
        views.delete_department_manager,
        name="department-manager-delete",
    ),
]
