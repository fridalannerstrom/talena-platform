from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

def send_invite_email(to_email, invite_link, company_name="", invited_by=""):
    subject = f"Du är inbjuden till Talena{f' ({company_name})' if company_name else ''}"
    text = f"""Hej!

Du har blivit inbjuden till Talena{f' för {company_name}' if company_name else ''}.
Klicka på länken för att välja lösenord och aktivera ditt konto:

{invite_link}

{f'Inbjudan skickades av: {invited_by}' if invited_by else ''}

/Talena
"""
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=[to_email],
    )
    msg.send()