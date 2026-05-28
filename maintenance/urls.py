from django.urls import path
from . import views

urlpatterns = [
    path('preview/', views.preview, name='maintenance_preview'),
]