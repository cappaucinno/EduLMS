from django.urls import path
from . import views

urlpatterns = [
    path('',                           views.dashboard,     name='superadmin_dashboard'),
    path('users/',                     views.user_list,     name='superadmin_users'),
    path('users/<int:pk>/approve/',    views.approve_user,  name='superadmin_approve'),
    path('users/<int:pk>/delete/',     views.delete_user,   name='superadmin_delete_user'),
    path('users/<int:pk>/resend/',     views.resend_setup,  name='superadmin_resend_setup'),
    path('rooms/',                     views.room_list,     name='superadmin_rooms'),
    path('errors/',                    views.error_list,    name='superadmin_errors'),
    path('errors/<int:pk>/resolve/',   views.error_resolve, name='superadmin_error_resolve'),
    path('maintenance/',               views.maintenance,   name='superadmin_maintenance'),
    path('settings/',                  views.site_settings, name='superadmin_settings'),
    path('api-docs/',                  views.api_docs,      name='superadmin_api_docs'),
]
