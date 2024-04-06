"""
mail.py

This module is used handle mail sent in thread
"""

import logging
from threading import Thread
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from employee.models import EmployeeWorkInformation
from payroll.views.views import payslip_pdf
from payroll.models.models import Payslip
from base.backends import ConfiguredEmailBackend

logger = logging.getLogger(__name__)


class MailSendThread(Thread):
    """
    MailSend
    """

    def __init__(self, request, result_dict, ids):
        Thread.__init__(self)
        self.result_dict = result_dict
        self.ids = ids
        self.request = request
        self.host = request.get_host()
        self.protocol = "https" if request.is_secure() else "http"

    def run(self) -> None:
        super().run()
        for record in list(self.result_dict.values()):
            html_message = render_to_string(
                "payroll/mail_templates/default.html",
                {
                    "record": record,
                    "host": self.host,
                    "protocol": self.protocol,
                },
            )
            attachments = []
            for instance in record["instances"]:
                response = payslip_pdf(self.request, instance.id)
                attachments.append(
                    (
                        f"{instance.get_payslip_title()}.pdf",
                        response.content,
                        "application/pdf",
                    )
                )
            email_backend = ConfiguredEmailBackend()
            email = EmailMessage(
                f"Hello, {record['instances'][0].get_name()} Your Payslips is Ready!",
                html_message,
                email_backend.dynamic_username_with_display_name,
                list(
                    EmployeeWorkInformation.objects.filter(
                        employee_id=record["instances"][0].employee_id
                    ).values_list("email", flat=True)
                ),
                # reply_to=["another@example.com"],
                # headers={"Message-ID": "foo"},
            )
            email.attachments = attachments

            # Send the email
            email.content_subtype = "html"
            try:
                email.send()
                Payslip.objects.filter(id__in=self.ids).update(sent_to_employee=True)
            except Exception as e:
                logger.exception(e)
                pass
        return
