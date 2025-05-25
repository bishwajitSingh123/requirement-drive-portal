from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template


# EMAIL_FROM="noreply@bishwajit.com"

def send_email(subject: str, email_to: list[str], html_template, context):
    msg = EmailMultiAlternatives(
        subject=subject, from_email="noreply@talentbase.com", to=email_to
    )
    html_template = get_template(html_template)
    html_alternative = html_template.render(context)
    msg.attach_alternative(html_alternative, "text/html")
    msg.send(fail_silently=False)
