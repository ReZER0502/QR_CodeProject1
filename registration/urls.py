from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('success/<int:attendee_id>/', views.success, name='success'),
    path('mark_attendance/', views.mark_attendance, name='mark_attendance'),
    path('download/<int:attendee_id>/', views.download_qr, name='download_qr'),
    path('admin/register/',views.register_admin, name='register_admin'),
    path('admin/dashboard/',views.admin_dashboard, name='admin_dashboard'),
    path('admin/login/', views.admin_login, name='admin_login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='admin_login'), name='logout'),
    path('download-attendees/', views.download_attendees_csv, name='download_attendees'),
    path('get-attendees-status/', views.get_attendees_status, name='get_attendees_status'),
    path('admin/reset_attendance/', views.reset_attendance, name='reset_attendance'),
    path('update-attendee-count/', views.update_attendee_count, name='update_attendee_count'),
]