from __future__ import annotations

import typing

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings

if typing.TYPE_CHECKING:
    from allauth.socialaccount.models import SocialLogin
    from django.http import HttpRequest

    from knowledgeassistant.users.models import User


# class AccountAdapter(DefaultAccountAdapter):
#     def is_open_for_signup(self, request: HttpRequest) -> bool:
#         return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

#     def get_signup_redirect_url(self, request: HttpRequest) -> str:  # type: ignore[override]
#         """Redirect to login with a flag so we can show a modal after signup.

#         When email verification is mandatory, users should be prompted to
#         check their inbox. We show this via a modal on the login page.
#         """
#         from django.urls import reverse

#         login_url = reverse("account_login")
#         return f"{login_url}?verification=sent"


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest) -> bool:
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def get_signup_redirect_url(self, request: HttpRequest) -> str:  # type: ignore[override]
        from django.urls import reverse
        login_url = reverse("account_login")
        return f"{login_url}?verification=sent"

    def send_confirmation_mail(self, request, emailconfirmation, signup):
        from django.template.loader import render_to_string
        from django.core.mail import EmailMultiAlternatives
        from django.urls import reverse

        current_site = request.get_host()
        activate_url = f"{request.scheme}://{current_site}{reverse('account_confirm_email', args=[emailconfirmation.key])}"

        ctx = {
            "user": emailconfirmation.email_address.user,
            "activate_url": activate_url,
            "current_site": current_site,
            "email": emailconfirmation.email_address.email,
            "request": request,
        }

        subject = render_to_string("account/email/email_confirmation_subject.txt", ctx).strip()
        text_body = render_to_string("account/email/email_confirmation_message.txt", ctx)
        html_body = render_to_string("account/email/email_confirmation_message.html", ctx)

        msg = EmailMultiAlternatives(subject, text_body, self.get_from_email(), [emailconfirmation.email_address.email])
        msg.attach_alternative(html_body, "text/html")
        msg.send()

class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(
        self,
        request: HttpRequest,
        sociallogin: SocialLogin,
    ) -> bool:
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def populate_user(
        self,
        request: HttpRequest,
        sociallogin: SocialLogin,
        data: dict[str, typing.Any],
    ) -> User:
        """
        Populates user information from social provider info.

        See: https://docs.allauth.org/en/latest/socialaccount/advanced.html#creating-and-populating-user-instances
        """
        user = super().populate_user(request, sociallogin, data)
        if not user.name:
            if name := data.get("name"):
                user.name = name
            elif first_name := data.get("first_name"):
                user.name = first_name
                if last_name := data.get("last_name"):
                    user.name += f" {last_name}"
        return user
