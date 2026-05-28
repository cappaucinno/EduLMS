from django.urls import path
from accounts.views import dashboard_redirect

urlpatterns = [
    path('', dashboard_redirect, name='dashboard'),
]
