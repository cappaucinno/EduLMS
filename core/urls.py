from django.urls import path
from . import dashboard_views, views

urlpatterns = [
    path('errors/',                    dashboard_views.error_list,   name='error_list'),
    path('errors/<int:pk>/',           dashboard_views.error_detail, name='error_detail'),
    path('errors/<int:pk>/resolve/',   dashboard_views.error_resolve, name='error_resolve'),
    path('errors/clear-resolved/',     dashboard_views.error_clear,  name='error_clear'),

    path('maintenance/preview/', views.maintenance_preview, name='maintenance_preview'),
]