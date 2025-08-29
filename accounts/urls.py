# accounts/urls.py
from django.urls import path
from .views import signup_api, login_api, logout_api, me, get_csrf_token

urlpatterns = [
    path("signup/", signup_api),
    path("login/", login_api),
    path("logout/", logout_api),
    path("me/", me),
    path("csrf/", get_csrf_token),
]
