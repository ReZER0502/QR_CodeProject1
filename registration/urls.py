from django.urls import path
from . import views
from .views import download_attendee_info


urlpatterns = [
    path('register/', views.register, name='register'),
    path('success/<int:attendee_id>/', views.success, name='success'),
    path('mark_attendance/', views.mark_attendance, name='mark_attendance'),
    path('download/<int:attendee_id>/', download_attendee_info, name='download_attendee_info'),
    path('admin/register/',views.register_admin, name='register_admin')
]
