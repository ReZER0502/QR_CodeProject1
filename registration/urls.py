from django.urls import path
from . import views
from .views import mark_attendance

urlpatterns = [
    path('register/', views.register, name='register'),
    path('success/<int:attendee_id>/', views.success, name='success'),
    path('mark_attendance/', views.mark_attendance, name='mark_attendance'),
]
