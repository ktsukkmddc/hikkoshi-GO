# app/views_custom_auth.py
from django.contrib.auth.views import PasswordResetView
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.translation import gettext as _


class CustomPasswordResetView(PasswordResetView):

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email,
                  html_email_template_name=None):

        # 件名の生成
        subject = render_to_string(subject_template_name, context)
        subject = "".join(subject.splitlines())  # 改行の除去

        # 本文の生成
        body = render_to_string(email_template_name, context)

        # EmailMessage を使う → あなたの SendGrid API backend が動く！
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=from_email,
            to=[to_email]
        )
        return email.send()  # ここで SendGridAPIEmailBackend が発動