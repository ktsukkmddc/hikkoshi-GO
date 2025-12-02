# app/email_backend.py

import sendgrid
from sendgrid.helpers.mail import Mail
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

print("=== SendGrid backend is being used ===")

class SendGridAPIEmailBackend(BaseEmailBackend):
    """
    Django の send_mail() / EmailMessage を
    SendGrid の Web API 経由で送信するバックエンド
    """

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        sent_count = 0

        for message in email_messages:
            # 宛先（to / cc / bcc を全部まとめる）
            to_list = list(message.to or [])
            cc_list = list(message.cc or [])
            bcc_list = list(message.bcc or [])
            all_to = to_list + cc_list + bcc_list

            if not all_to:
                continue

            from_email = message.from_email or settings.DEFAULT_FROM_EMAIL

            # 本文の扱い（テキスト or HTML）
            body = message.body or ""
            if message.content_subtype == "html":
                mail = Mail(
                    from_email=from_email,
                    to_emails=all_to,
                    subject=message.subject,
                    html_content=body,
                )
            else:
                # プレーンテキスト
                mail = Mail(
                    from_email=from_email,
                    to_emails=all_to,
                    subject=message.subject,
                    plain_text_content=body,
                )

            # ヘッダーがあれば反映（ほぼ使っていないと思うけど一応）
            if message.extra_headers:
                mail.headers = message.extra_headers

            try:
                response = sg.send(mail)
                if 200 <= response.status_code < 300:
                    sent_count += 1
            except Exception as e:
                # 失敗してもアプリ全体は落とさない
                if self.fail_silently:
                    continue
                else:
                    raise e

        return sent_count