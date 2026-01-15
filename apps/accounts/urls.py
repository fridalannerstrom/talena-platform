from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from .views import post_login_redirect
from .views import accept_invite, invite_user

app_name = "accounts"

urlpatterns = [
    path("login/", LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("go/", post_login_redirect, name="post_login_redirect"),
    path("accounts/users/invite/", invite_user, name="invite_user"),
    path("invite/accept/<uidb64>/<token>/", accept_invite, name="accept_invite"),
]